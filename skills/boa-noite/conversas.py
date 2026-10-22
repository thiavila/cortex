#!/usr/bin/env python3
"""Extrai o trecho NOVO de cada conversa do escopo para o resumo do /boa-noite (macOS, Windows e Linux).

Duas fontes (--backend):
- app: as conversas do app desktop do Claude. Os metadados (título, pasta, branch, arquivada, última atividade) vêm
  da pasta do app (`<app>/claude-code-sessions/<conta>/<org>/local_*.json`; a pasta do app sai de caminhos.pastas_app():
  a do próprio CLAUDE_CODE_EXECPATH primeiro, senão `Claude*` em ~/Library/Application Support, %APPDATA% ou
  ~/.config; --app-dir força outra). Só entram conversas da mesma conta/org da conversa atual: uma conta anterior do
  mesmo app não pode vazar para este quadro. Id = `local_…`, link = `claude://claude.ai/epitaxy/<id>`.
  Tudo o que depende desse layout interno do app fica em layout_app(); se ele mudar, o erro diz o que fazer.
- transcritos: só os transcritos locais do Claude Code (CLI, IDE, ou máquina sem o app):
  `<projects>/*/<uuid>.jsonl` da pasta de config ativa (a que tem a conversa atual; senão $CLAUDE_CONFIG_DIR ou
  ~/.claude). Só o nível de cima de cada projeto (subagentes ficam de fora, e registros de sidechain também);
  sessões headless/SDK (`claude -p`, rotinas) ficam de fora sem --incluir-sdk. Id = `cli:<uuid>`, link = null,
  retomar = `claude --resume <uuid>`. Transcrito aberto pelo app desktop, quando o app está na máquina, sai com o id
  `local_…` e o link do app (o mesmo id que os cards já têm); se ela for de outra conta/org do app
  ($CLAUDE_CODE_ACCOUNT_UUID / $CLAUDE_CODE_ORGANIZATION_UUID, quando existem), fica de fora.
- auto (padrão): app quando há pasta do app E a conversa de --sessao está nela; senão transcritos. Uma linha no
  stderr diz qual foi e por quê.

Transcritos: `<config>/projects/*/<cliSessionId>.jsonl`, em $CLAUDE_CONFIG_DIR e ~/.claude. Guarda um cursor por
conversa (último uuid já resumido) e escreve, para cada conversa com novidade, um .txt só com as falas do usuário e o
texto do assistente (sem thinking, sem tool results), dividido em partes de até --max-chars (nada é cortado: o
resumo lê todas as partes). Datas: todo timestamp é convertido para o --fuso antes de comparar com --desde.

Uso (sempre com o lançador `sh <skills>/tarefas/py`):
  conversas.py extrair [--sessao <id desta conversa>] [--quadro <id do artefato>] --saida <dir> [--desde AAAA-MM-DD]
                       [--fuso <IANA>] [--backend auto|app|transcritos] [--max-chars 14000] [--incluir-arquivadas]
                       [--incluir-sdk] [--app-dir <dir>]
  conversas.py confirmar [--quadro <id do artefato>] --manifesto <dir>/manifesto.json --ids local_a,cli:<uuid>
  --sessao: a conversa atual: `local_…` (app, get_session "self") ou `cli:<uuid>`/`<uuid>` (o `sessao=` do aviso do
            hook). Sem ela: $CLAUDE_CODE_HOST_SESSION_ID (app) ou $CLAUDE_CODE_SESSION_ID. A atual não se resume.
  --fuso: config/preferencias.fuso (IANA). Sem ele, o fuso do sistema. --desde padrão = ontem nesse fuso.
  --desde: app: só vale para conversa com cursor perdido (transcript reescrito), que volta a ser lida por data;
           conversa sem cursor entra inteira (manifesto: primeira_leitura). transcritos: sem cursor, só entram os
           transcritos com atividade a partir de --desde (inteiros), para não engolir o histórico todo; com cursor,
           só o que veio depois dele.
  --quadro: id do artefato do quadro (o fim da URL); os cursores são por quadro. Sem quadro: cursores "sem-quadro".
            Ficam em <dados>/state/boa-noite-cursores-quadro-<id>.json (<dados>: ver tarefas/caminhos.py); se ainda
            não existir, lê o de ~/.claude/state (de antes da v0.3) e o `confirmar` grava no novo.
  confirmar: depois que o resumo foi gravado no quadro, avança os cursores; sem isso a próxima rodada relê o mesmo
             trecho.
Manifesto (um item por conversa com novidade): id, titulo, cwd, branch, arquivada, ultima_atividade (no --fuso),
rotina, repetida (rotinas), arquivos, cursor_perdido, primeira_leitura, chars, cursor_novo, link, retomar, backend.
"""
import argparse
import datetime as dt
import glob
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tarefas"))
import caminhos  # noqa: E402

JANELA_CURSOR = 30  # transcritos: com cursor, só relê arquivo mexido nos 30 dias antes de --desde


class ErroApp(Exception):
    """O app desktop não está aqui, a conversa não está nele, ou o layout interno dele mudou."""


def aviso(msg):
    print(msg, file=sys.stderr)


# --- cursores ---------------------------------------------------------------------------------------------------

def _nome_estado(a):
    return f"boa-noite-cursores-quadro-{a.quadro or 'sem-quadro'}.json"


def estado_novo(a):
    """Arquivo de cursores do quadro (sem quadro: "sem-quadro"). Não herda cursores de outro quadro."""
    return os.path.join(caminhos.dados(), "state", _nome_estado(a))


def ler_estado(a):
    for p in (estado_novo(a), os.path.join(caminhos.legado(), "state", _nome_estado(a))):
        if os.path.exists(p):
            try:
                with open(p, encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return {}
    return {}


# --- transcritos ------------------------------------------------------------------------------------------------

def ler_jsonl(p):
    out = []
    with open(p, encoding="utf-8", errors="replace") as f:
        for l in f:
            try:
                d = json.loads(l)
            except Exception:
                continue
            if isinstance(d, dict):
                out.append(d)
    return out


def texto_msg(d):
    m = d.get("message") or {}
    c = m.get("content")
    if isinstance(c, str):
        return c
    out = []
    for b in c or []:
        if isinstance(b, dict) and b.get("type") == "text":
            out.append(b.get("text", ""))
    return "\n".join(out)


def achar_transcript(cli):
    if not cli or not re.fullmatch(r"[A-Za-z0-9_-]+", cli):
        return None
    hits = [h for p in caminhos.pastas_projects() for h in glob.glob(os.path.join(p, "*", f"{cli}.jsonl"))]
    return hits[0] if hits else None


def uuid_de(sessao):
    """`cli:<uuid>` ou `<uuid>` → `<uuid>`; `local_…` → None (só o app sabe o uuid dela)."""
    s = (sessao or "").strip()
    if s.startswith("cli:"):
        s = s[4:]
    if not s or s.startswith("local_") or not re.fullmatch(r"[A-Za-z0-9_-]+", s):
        return None
    return s


# --- app desktop (único lugar que conhece o layout interno dele) ------------------------------------------------

def bases_app(forcada=None):
    if forcada:
        p = os.path.abspath(os.path.expanduser(forcada))
        if os.path.isdir(os.path.join(p, "claude-code-sessions")):
            p = os.path.join(p, "claude-code-sessions")
        return [p]
    return [os.path.join(p, "claude-code-sessions") for p in caminhos.pastas_app()]


def _ler_meta(f):
    with open(f, encoding="utf-8") as h:
        d = json.load(h)
    if not isinstance(d, dict) or not str(d.get("sessionId", "")).startswith("local_"):
        raise ValueError("sem sessionId local_")
    return d


def layout_app(bases, sessao):
    """Acha a conversa `sessao` (local_… ou o uuid do CLI dela) nas pastas do app e devolve
    (pasta da conta/org, sessionId dela, [metadados normalizados das conversas dessa conta/org]).

    Layout assumido: <base>/<conta>/<org>/local_*.json com sessionId, cliSessionId, title, cwd, branch, isArchived,
    lastActivityAt (ms). Qualquer coisa fora disso vira ErroApp com o motivo."""
    bases = [b for b in bases if os.path.isdir(b)]
    if not bases:
        raise ErroApp("app desktop do Claude não encontrado nesta máquina (nenhuma pasta claude-code-sessions)")
    local = sessao if (sessao or "").startswith("local_") else None
    cli = None if local else uuid_de(sessao)
    if not local and not cli:
        raise ErroApp("sem --sessao (nem $CLAUDE_CODE_HOST_SESSION_ID) para achar a conta no app")
    achou = None
    for base in bases:
        arqs = glob.glob(os.path.join(base, "*", "*", "local_*.json"))
        for f in arqs:
            if local:
                if os.path.basename(f) == f"{local}.json":
                    achou = f
            else:
                try:
                    if _ler_meta(f).get("cliSessionId") == cli:
                        achou = f
                except Exception:
                    continue
            if achou:
                break
        if achou:
            break
    if not achou:
        raise ErroApp(f"conversa {sessao} não encontrada no app ({'; '.join(bases)})")
    try:
        atual = _ler_meta(achou)["sessionId"]
    except Exception as e:
        raise ErroApp(f"metadados do app em formato desconhecido ({achou}: {e})")
    pasta = os.path.dirname(achou)
    sessoes = []
    for f in glob.glob(os.path.join(pasta, "local_*.json")):
        try:
            d = _ler_meta(f)
        except Exception:
            continue
        sessoes.append({"id": d["sessionId"], "cli": str(d.get("cliSessionId") or ""), "titulo": d.get("title") or "",
                        "cwd": d.get("cwd") or "", "branch": d.get("branch"), "arquivada": bool(d.get("isArchived")),
                        "ultima_ms": d.get("lastActivityAt") or 0})
    return pasta, atual, sessoes


def mapa_app_por_cli(bases):
    """cliSessionId → metadados do app, em todas as pastas do app (para transcritos abertos pelo app)."""
    out = {}
    for base in bases:
        for f in glob.glob(os.path.join(base, "*", "*", "local_*.json")):
            try:
                d = _ler_meta(f)
            except Exception:
                continue
            if d.get("cliSessionId"):
                org_dir = os.path.dirname(f)
                out[str(d["cliSessionId"])] = {"id": d["sessionId"], "titulo": d.get("title") or "",
                                               "arquivada": bool(d.get("isArchived")),
                                               "conta": (os.path.basename(os.path.dirname(org_dir)), os.path.basename(org_dir))}
    return out


def link_app(sid):
    return f"claude://claude.ai/epitaxy/{sid}"


# --- trecho novo de uma conversa --------------------------------------------------------------------------------

def _local_ingenuo(d):
    return d.replace(tzinfo=None).isoformat(timespec="minutes") if d else ""


def trecho(registros, cursor, desde, tz):
    """(linhas, cursor_novo, perdido, rotina) com o que veio depois do cursor (sem cursor: tudo)."""
    perdido = cursor is not None and not any(r.get("uuid") == cursor for r in registros)
    if perdido:
        cursor = None  # transcript reescrito: volta a ler pela data e marca no manifesto
    linhas, passou, ultimo, rotina = [], cursor is None, None, False
    for d in registros:
        if d.get("type") not in ("user", "assistant") or d.get("isSidechain") or d.get("isMeta"):
            continue
        u = d.get("uuid")
        if not passou:
            if u == cursor:
                passou = True
            continue
        quando = caminhos.no_fuso(d.get("timestamp"), tz)
        if perdido and quando and quando.date() < desde:
            ultimo = u
            continue
        t = texto_msg(d).strip()
        if not t or t.startswith("<command-") or t.startswith("<local-command"):
            ultimo = u
            continue
        if d["type"] == "user" and t.startswith("<scheduled-task"):
            rotina = True
        quem = "USUÁRIO" if d["type"] == "user" else "ASSISTENTE"
        hora = quando.strftime("%Y-%m-%dT%H:%M") if quando else str(d.get("timestamp", ""))[:16]
        linhas.append(f"[{hora}] {quem}: {t}")
        ultimo = u
    return linhas, ultimo, perdido, rotina


def gravar_partes(saida, nome, linhas, max_chars):
    partes, atual = [], ""
    for ln in linhas:
        if atual and len(atual) + len(ln) > max_chars:
            partes.append(atual)
            atual = ""
        atual += ("\n\n" if atual else "") + ln[:max_chars]
    if atual:
        partes.append(atual)
    arqs = []
    for n, corpo in enumerate(partes, 1):
        arq = os.path.join(saida, f"{nome}-{n}.txt")
        with open(arq, "w", encoding="utf-8") as f:
            f.write(corpo)
        arqs.append(arq)
    return arqs, sum(len(p) for p in partes)


# --- fontes por backend -----------------------------------------------------------------------------------------

def fontes_app(a, ctx, tz):
    """(meta, registros) de cada conversa da conta/org da conversa atual no app."""
    _, atual, sessoes = ctx
    for s in sessoes:
        if s["arquivada"] and not a.incluir_arquivadas:
            continue
        if s["id"] == atual:  # a própria rodada do /boa-noite não se resume
            continue
        # Conversa aberta que nunca foi resumida entra inteira, seja qual for a data: uma rodada pulada ou
        # uma janela curta não podem esconder conversa do fechamento. Com cursor, só entra o que veio depois dele.
        tp = achar_transcript(s["cli"])
        if not tp:
            continue
        ult = dt.datetime.fromtimestamp((s["ultima_ms"] or 0) / 1000, tz=dt.timezone.utc)
        ult = ult.astimezone(tz) if tz else ult.astimezone()
        yield ({"id": s["id"], "titulo": s["titulo"], "cwd": s["cwd"], "branch": s["branch"], "arquivada": s["arquivada"],
                "ultima": ult, "link": link_app(s["id"]), "retomar": None, "backend": "app"}, ler_jsonl(tp))


def _titulo_curto(t, n=60):
    t = re.sub(r"\s+", " ", t).strip()
    return t if len(t) <= n else t[: n - 1].rstrip() + "…"


def meta_transcrito(registros, tz):
    resumo = titulo_custom = primeira = cwd = branch = None
    ultima, entradas = None, set()
    for d in registros:
        tp = d.get("type")
        if tp == "summary" and d.get("summary") and not resumo:
            resumo = str(d["summary"])
        elif tp == "custom-title" and d.get("customTitle"):
            titulo_custom = str(d["customTitle"])  # fica o último (renomeação)
        if d.get("isSidechain"):
            continue
        if d.get("cwd"):
            cwd = d["cwd"]
        if d.get("gitBranch"):
            branch = d["gitBranch"]
        if tp not in ("user", "assistant") or d.get("isMeta"):
            continue
        if d.get("entrypoint"):
            entradas.add(str(d["entrypoint"]))
        q = caminhos.no_fuso(d.get("timestamp"), tz)
        if q and (ultima is None or q > ultima):
            ultima = q
        if tp == "user" and primeira is None:
            t = texto_msg(d).strip()
            if t and not t.startswith("<"):
                primeira = t
    return {"titulo": _titulo_curto(resumo or titulo_custom or primeira or ""), "cwd": cwd or "", "branch": branch,
            "ultima": ultima, "sdk": bool(entradas) and all(e.startswith("sdk") for e in entradas),
            "app": "claude-desktop" in entradas}


def fontes_transcritos(a, tz, desde, st):
    atual = uuid_de(a.sessao)
    if not atual and (a.sessao or "").startswith("local_"):
        try:  # conversa do app rodando em modo transcritos: o uuid dela está nos metadados do app
            _, _, sess = layout_app(bases_app(a.app_dir), a.sessao)
            atual = next((s["cli"] for s in sess if s["id"] == a.sessao), None)
        except ErroApp:
            pass
    if not atual:
        aviso("conversas: não sei qual é a conversa atual (passe --sessao cli:<uuid>); ela pode entrar no manifesto")
    raizes = caminhos.pastas_projects()
    if not raizes:
        raise SystemExit("Nenhuma pasta de transcritos (<config>/projects) encontrada. / No transcripts folder found.")
    raiz = raizes[0]  # a da conta ativa; outra só se a conversa atual estiver nela
    if atual:
        raiz = next((r for r in raizes if glob.glob(os.path.join(r, "*", f"{atual}.jsonl"))), raiz)
    ini = dt.datetime.combine(desde, dt.time.min)
    ini = ini.replace(tzinfo=tz) if tz else ini.astimezone()
    corte_novo, corte_cursor = ini.timestamp(), (ini - dt.timedelta(days=JANELA_CURSOR)).timestamp()
    app_bases, mapa = bases_app(a.app_dir), None
    conta_env = (os.environ.get("CLAUDE_CODE_ACCOUNT_UUID", ""), os.environ.get("CLAUDE_CODE_ORGANIZATION_UUID", ""))
    for f in sorted(glob.glob(os.path.join(raiz, "*", "*.jsonl"))):
        uid = os.path.splitext(os.path.basename(f))[0]
        if uid == atual or not re.fullmatch(r"[A-Za-z0-9_-]+", uid):
            continue
        try:
            mt = os.path.getmtime(f)
        except OSError:
            continue
        mid = f"cli:{uid}"
        if mt < (corte_cursor if mid in st else corte_novo):
            continue  # nada mexeu nele no período: nem abre
        registros = ler_jsonl(f)
        m = meta_transcrito(registros, tz)
        if m["sdk"] and not a.incluir_sdk:
            continue
        meta = {"id": mid, "titulo": m["titulo"], "cwd": m["cwd"], "branch": m["branch"], "arquivada": False,
                "ultima": m["ultima"], "link": None, "retomar": f"claude --resume {uid}", "backend": "transcritos"}
        if m["app"] and app_bases:
            if mapa is None:
                mapa = mapa_app_por_cli(app_bases)
            s = mapa.get(uid)
            if s:  # aberta pelo app: mesmo id e link que os cards já usam
                if s["id"] == a.sessao or (s["arquivada"] and not a.incluir_arquivadas):
                    continue
                if any(x and x != y for x, y in zip(conta_env, s["conta"])):
                    continue  # conversa do app em outra conta/org (o app guarda <conta>/<org>): não vaza para este quadro
                meta.update(id=s["id"], titulo=s["titulo"] or meta["titulo"], arquivada=s["arquivada"],
                            link=link_app(s["id"]), retomar=None)
        if meta["id"] not in st and (meta["ultima"] is None or meta["ultima"].date() < desde):
            continue  # primeira leitura só para quem teve atividade a partir de --desde
        yield meta, registros


# --- comandos ---------------------------------------------------------------------------------------------------

def escolher_backend(a):
    """('app', ctx) ou ('transcritos', None)."""
    if a.backend == "transcritos":
        return "transcritos", None
    try:
        ctx = layout_app(bases_app(a.app_dir), a.sessao)
    except ErroApp as e:
        if a.backend == "app":
            sys.exit(f"conversas --backend app: {e}.\nUse --backend transcritos (transcritos locais do Claude Code) "
                     f"ou as ferramentas de sessão do app (list_sessions / list_events).")
        aviso(f"conversas: backend transcritos ({e})")
        return "transcritos", None
    if a.backend == "auto":
        aviso(f"conversas: backend app (conversa {a.sessao} achada em {ctx[0]})")
    return "app", ctx


def extrair(a):
    tz = caminhos.fuso(a.fuso)
    st = ler_estado(a)
    desde = dt.date.fromisoformat(a.desde) if a.desde else caminhos.hoje(tz) - dt.timedelta(days=1)
    os.makedirs(a.saida, exist_ok=True)
    backend, ctx = escolher_backend(a)
    fontes = fontes_app(a, ctx, tz) if backend == "app" else fontes_transcritos(a, tz, desde, st)
    man = []
    for meta, registros in fontes:
        cursor = st.get(meta["id"])
        linhas, ultimo, perdido, rotina = trecho(registros, cursor, desde, tz)
        if not linhas:
            continue
        arqs, chars = gravar_partes(a.saida, re.sub(r"[^A-Za-z0-9_-]", "-", meta["id"]), linhas, a.max_chars)
        man.append({"id": meta["id"], "titulo": meta["titulo"], "cwd": meta["cwd"], "branch": meta["branch"],
                    "arquivada": meta["arquivada"], "ultima_atividade": _local_ingenuo(meta["ultima"]),
                    "rotina": rotina, "arquivos": arqs, "cursor_perdido": perdido, "primeira_leitura": meta["id"] not in st,
                    "chars": chars, "cursor_novo": ultimo, "link": meta["link"], "retomar": meta["retomar"],
                    "backend": meta["backend"]})
    man.sort(key=lambda x: x["ultima_atividade"], reverse=True)
    # Execuções de rotina agendada: só a mais recente de cada título vai para o resumo; as outras ficam
    # marcadas como "repetida" (o /boa-noite propõe arquivar todas menos a última).
    vistos = set()
    for m in man:
        if m["rotina"]:
            m["repetida"] = m["titulo"] in vistos
            vistos.add(m["titulo"])
    pm = os.path.join(a.saida, "manifesto.json")
    with open(pm, "w", encoding="utf-8") as f:
        json.dump(man, f, ensure_ascii=False, indent=1)
    print(json.dumps({"conversas": len(man), "chars_total": sum(m["chars"] for m in man), "backend": backend,
                      "desde": desde.isoformat(), "manifesto": pm}, ensure_ascii=False))


def confirmar(a):
    st = ler_estado(a)
    ids = set(x.strip() for x in a.ids.split(",") if x.strip()) if a.ids else None
    with open(a.manifesto, encoding="utf-8") as f:
        manifesto = json.load(f)
    for m in manifesto:
        if ids is not None and m["id"] not in ids:
            continue
        if m.get("cursor_novo"):
            st[m["id"]] = m["cursor_novo"]
    p = estado_novo(a)
    os.makedirs(os.path.dirname(p), exist_ok=True)
    tmp = p + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(st, f, indent=1)
    os.replace(tmp, p)
    print(f"cursores: {len(st)}")


def slug_id(v):
    v = v.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", v):
        raise argparse.ArgumentTypeError("quadro: id ou URL do artefato")
    return v


def sessao_padrao():
    h = os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", "")
    if h.startswith("local_"):
        return h
    s = os.environ.get("CLAUDE_CODE_SESSION_ID", "")
    return f"cli:{s}" if s else None


def main(argv=None):
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("extrair"); e.add_argument("--quadro", type=slug_id); e.add_argument("--saida", required=True)
    e.add_argument("--sessao", default=sessao_padrao(),
                   help="conversa atual: local_… (app) ou cli:<uuid>; limita à conta dela e fica de fora")
    e.add_argument("--backend", choices=["auto", "app", "transcritos"], default="auto")
    e.add_argument("--fuso", help="IANA do quadro (config/preferencias.fuso); padrão: o do sistema")
    e.add_argument("--app-dir", help="pasta do app ou a claude-code-sessions dele (padrão: a do app desta sessão)")
    e.add_argument("--desde"); e.add_argument("--max-chars", type=int, default=14000)
    e.add_argument("--incluir-arquivadas", action="store_true")
    e.add_argument("--incluir-sdk", action="store_true", help="transcritos: incluir sessões headless/SDK (claude -p)")
    c = sp.add_parser("confirmar"); c.add_argument("--quadro", type=slug_id); c.add_argument("--manifesto", required=True)
    c.add_argument("--ids", help="só estas conversas (separadas por vírgula): as que tiveram o resumo gravado no quadro")
    a = ap.parse_args(argv)
    {"extrair": extrair, "confirmar": confirmar}[a.cmd](a)


if __name__ == "__main__":
    main()

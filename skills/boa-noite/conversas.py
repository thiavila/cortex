#!/usr/bin/env python3
"""Extrai o trecho NOVO de cada conversa do escopo para o resumo do /boa-noite.

Lê os metadados das conversas do app em que está rodando (~/Library/Application Support/<app>/claude-code-sessions,
com <app> tirado do próprio CLAUDE_CODE_EXECPATH; --app-dir força outro) e os transcripts
(<config>/projects/*/<cliSessionId>.jsonl, em $CLAUDE_CONFIG_DIR ou ~/.claude), guarda um
cursor por conversa (último uuid já resumido) e escreve, para cada conversa com novidade, um .txt só com
as falas do usuário e o texto do assistente (sem thinking, sem tool results), dividido em partes de até
--max-chars (nada é cortado: o resumo lê todas as partes).

Uso:
  python3 conversas.py extrair --sessao <sessionId desta conversa> [--quadro <id do artefato>] --saida <dir> [--desde AAAA-MM-DD] [--max-chars 14000] [--incluir-arquivadas] [--app-dir <dir>]
  python3 conversas.py confirmar [--quadro <id do artefato>] --manifesto <dir>/manifesto.json --ids local_a,local_b
  --desde: só vale para conversa com cursor perdido (transcript reescrito), que volta a ser lida por data. Conversa
           sem cursor entra inteira (manifesto: primeira_leitura); com cursor, só o que veio depois dele.
  --quadro: id do artefato do quadro (o fim da URL); os cursores são por quadro. Sem quadro: cursores "sem-quadro".
  --sessao: a conversa atual (get_session "self"). Só entram conversas da mesma conta dela: o app guarda as de cada
            conta numa pasta <conta>/<org>/, e uma conta anterior do mesmo app não pode vazar para este quadro.
     (depois que o resumo foi gravado no quadro: avança os cursores; sem isso a próxima rodada relê o mesmo trecho)
"""
import argparse, datetime as dt, glob, json, os, re, sys

STATE = os.path.expanduser("~/.claude/state/boa-noite-cursores-{}.json")


def estado(a):
    """Arquivo de cursores do quadro (sem quadro: "sem-quadro"). Não herda cursores de outro quadro."""
    return STATE.format("quadro-" + (a.quadro or "sem-quadro"))


PROJS = []
for d in (os.environ.get("CLAUDE_CONFIG_DIR"), "~/.claude"):
    p = os.path.join(os.path.expanduser(d), "projects") if d else None
    if p and os.path.isdir(p) and p not in PROJS:
        PROJS.append(p)


def pasta_app(forcada=None):
    """Pasta de conversas do app em que esta sessão roda (cada app/conta tem a sua)."""
    if forcada:
        return os.path.expanduser(forcada)
    m = re.search(r"(.*/Application Support/[^/]+)/", os.environ.get("CLAUDE_CODE_EXECPATH", ""))
    if not m:
        sys.exit("Não achei o app pelo CLAUDE_CODE_EXECPATH; rode dentro do app do Claude ou passe --app-dir.")
    return os.path.join(m.group(1), "claude-code-sessions")


def pasta_conta(base, sessao=None):
    """<base>/<conta>/<org> da conversa atual."""
    todos = glob.glob(os.path.join(base, "*", "*", "local_*.json"))
    achou = [f for f in todos if os.path.basename(f) == f"{sessao}.json"]
    if not achou:
        sys.exit(f"Conversa {sessao} não encontrada em {base}.")
    return os.path.dirname(achou[0])


def sessoes(pasta):
    for f in glob.glob(os.path.join(pasta, "local_*.json")):
        try:
            d = json.load(open(f))
        except Exception:
            continue
        yield d


def achar_transcript(cli):
    hits = [h for p in PROJS for h in glob.glob(os.path.join(p, "*", f"{cli}.jsonl"))]
    return hits[0] if hits else None


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


def extrair(a):
    ep = estado(a)
    st = json.load(open(ep)) if os.path.exists(ep) else {}
    desde = a.desde or (dt.date.today() - dt.timedelta(days=1)).isoformat()
    os.makedirs(a.saida, exist_ok=True)
    man = []
    for s in sessoes(pasta_conta(pasta_app(a.app_dir), a.sessao)):
        if s.get("isArchived") and not a.incluir_arquivadas:
            continue
        if s["sessionId"] == a.sessao:  # a própria rodada do /boa-noite não se resume
            continue
        # Conversa aberta que nunca foi resumida entra inteira, seja qual for a data: uma rodada pulada ou
        # uma janela curta não podem esconder conversa do fechamento. Com cursor, só entra o que veio depois dele.
        tp = achar_transcript(s.get("cliSessionId", ""))
        if not tp:
            continue
        cursor = st.get(s["sessionId"])
        registros = []
        for l in open(tp, encoding="utf-8", errors="replace"):
            try:
                registros.append(json.loads(l))
            except Exception:
                pass
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
            if perdido and d.get("timestamp", "") < desde:
                ultimo = u
                continue
            t = texto_msg(d).strip()
            if not t or t.startswith("<command-") or t.startswith("<local-command"):
                ultimo = u
                continue
            if d["type"] == "user" and t.startswith("<scheduled-task"):
                rotina = True
            quem = "USUÁRIO" if d["type"] == "user" else "ASSISTENTE"
            linhas.append(f"[{d.get('timestamp', '')[:16]}] {quem}: {t}")
            ultimo = u
        if not linhas:
            continue
        partes, atual = [], ""
        for ln in linhas:
            if atual and len(atual) + len(ln) > a.max_chars:
                partes.append(atual); atual = ""
            atual += ("\n\n" if atual else "") + ln[: a.max_chars]
        if atual:
            partes.append(atual)
        arqs = []
        for n, corpo in enumerate(partes, 1):
            arq = os.path.join(a.saida, f"{s['sessionId']}-{n}.txt")
            open(arq, "w", encoding="utf-8").write(corpo)
            arqs.append(arq)
        corpo = "".join(partes)
        man.append({"id": s["sessionId"], "titulo": s.get("title", ""), "cwd": s.get("cwd", ""), "branch": s.get("branch"),
                    "arquivada": bool(s.get("isArchived")), "ultima_atividade": dt.datetime.fromtimestamp((s.get("lastActivityAt") or 0) / 1000).isoformat(timespec="minutes"),
                    "rotina": rotina, "arquivos": arqs, "cursor_perdido": perdido, "primeira_leitura": s["sessionId"] not in st, "chars": len(corpo), "cursor_novo": ultimo,
                    "link": f"claude://claude.ai/epitaxy/{s['sessionId']}"})
    man.sort(key=lambda x: x["ultima_atividade"], reverse=True)
    # Execuções de rotina agendada: só a mais recente de cada título vai para o resumo; as outras ficam
    # marcadas como "repetida" (o /boa-noite propõe arquivar todas menos a última).
    vistos = set()
    for m in man:
        if m["rotina"]:
            m["repetida"] = m["titulo"] in vistos
            vistos.add(m["titulo"])
    json.dump(man, open(os.path.join(a.saida, "manifesto.json"), "w"), ensure_ascii=False, indent=1)
    print(json.dumps({"conversas": len(man), "chars_total": sum(m["chars"] for m in man),
                      "manifesto": os.path.join(a.saida, "manifesto.json")}, ensure_ascii=False))


def confirmar(a):
    p = estado(a)
    st = json.load(open(p)) if os.path.exists(p) else {}
    ids = set(a.ids.split(",")) if a.ids else None
    for m in json.load(open(a.manifesto)):
        if ids is not None and m["id"] not in ids:
            continue
        if m.get("cursor_novo"):
            st[m["id"]] = m["cursor_novo"]
    os.makedirs(os.path.dirname(p), exist_ok=True)
    json.dump(st, open(p, "w"), indent=1)
    print(f"cursores: {len(st)}")


def slug_id(v):
    v = v.rstrip("/").rsplit("/", 1)[-1]
    if not re.fullmatch(r"[A-Za-z0-9_-]{6,64}", v):
        raise argparse.ArgumentTypeError("quadro: id ou URL do artefato")
    return v


def slug(v):
    if not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,40}", v):
        raise argparse.ArgumentTypeError("escopo: letras minúsculas, números, - e _")
    return v


ap = argparse.ArgumentParser()
sp = ap.add_subparsers(dest="cmd", required=True)
e = sp.add_parser("extrair"); e.add_argument("--quadro", type=slug_id); e.add_argument("--saida", required=True)
e.add_argument("--sessao", required=True, help="sessionId da conversa atual (local_…): limita à conta dela")
e.add_argument("--app-dir", help="pasta claude-code-sessions de outro app (padrão: a do app desta sessão)")
e.add_argument("--desde"); e.add_argument("--max-chars", type=int, default=14000); e.add_argument("--incluir-arquivadas", action="store_true")
c = sp.add_parser("confirmar"); c.add_argument("--quadro", type=slug_id); c.add_argument("--manifesto", required=True)
c.add_argument("--ids", help="só estas conversas (separadas por vírgula): as que tiveram o resumo gravado no quadro")
a = ap.parse_args()
{"extrair": extrair, "confirmar": confirmar}[a.cmd](a)

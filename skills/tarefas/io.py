#!/usr/bin/env python3
"""Import/export do quadro de tarefas (modelo v1, ver SCHEMA.md).

Roda com `sh <skills>/tarefas/py io.py …`. `--idioma` (padrão pt-BR; pt* = português, outro = inglês) define a
língua dos textos gerados: Markdown do export, prévia do plan e linhas de histórico do import.

export: junta os documentos baixados com `ArtifactData list ... out_dir=<dir>` num pacote (tasks, dias, arquivo,
  config e recorrentes).
  io.py export --dir <out_dir> --escopo <escopo> --out pacote.json [--csv x.csv] [--md x.md] [--idioma en]

plan: compara um pacote (ou uma lista de tarefas vinda de outro sistema, já no formato v1)
  com o índice atual e gera os arquivos de escrita + uma prévia legível.
  io.py plan --entrada pacote.json --indice indice.json --saida <dir> [--com-config] [--idioma en]
  -> <dir>/preview.md, <dir>/writes-N.json (lotes de até 45 escritas, com file_path absolutos)
  --com-config (só quadro NOVO): também `set` dos docs de dias/arquivo/config/recorrentes do pacote
  (marcados so_quadro_novo).

Casamento: mesma chave externa (`chaves`) = mesma tarefa (atualiza); senão, mesmo id; senão, nova.
"""
import argparse, csv, datetime as dt, glob, hashlib, json, os, re, sys, unicodedata

IDIOMA = "pt-BR"  # o --idioma da linha de comando (main)
NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
CAMPOS = ["titulo", "status", "resolucao", "prioridade", "area", "projeto", "projetos", "tags", "chaves", "pai", "relacionadas",
          "prazo", "proximo_passo", "contexto", "resumo", "links", "conversas", "historico", "fonte", "auto", "recorrente",
          "criado_em", "atualizado_em", "concluido_em"]
COLECOES_CONFIG = ["dias", "arquivo", "config", "recorrentes"]  # vão no pacote; no plan, só com --com-config (quadro novo)
STATUS = {"entrada", "a_fazer", "fazendo", "esperando", "feito"}

TXT = {
    "pt": {"md_titulo": "# Quadro {escopo} — exportado em {data}", "sem_projeto": "Sem projeto", "prazo": "prazo {d}",
           "status": {"entrada": "Entrada", "a_fazer": "A fazer", "fazendo": "Fazendo", "esperando": "Esperando", "feito": "Feito"},
           "importada": "Importada", "atualizada": "Atualizada por import",
           "prev_titulo": "# Prévia do import ({novas} novas, {atualizadas} atualizadas, {extras} docs de dias/arquivo/config/recorrentes, {conflitos} conflitos)",
           "prev_novas": "## Novas",
           "prev_atualizadas": "## Atualizadas (mesma chave; só título/status/prazo/prioridade/projeto/próximo passo, arrays unidos)",
           "prev_conflitos": "## Conflitos (não entram)",
           "prev_extras": "⚠️ Os docs de dias/arquivo/config/recorrentes SUBSTITUEM os existentes: use só em quadro novo.",
           "prev_indice": "Índice: `update` em indice/ativos com {p} (merge por id).",
           "conf_chave": "`{t}`: chave {k} repetida no arquivo (fica só a primeira)",
           "conf_mesma": "`{t}` e `{o}` casam com a mesma tarefa `{a}` (fica só a primeira)",
           "sem_titulo": "(sem título)"},
    "en": {"md_titulo": "# Board {escopo} — exported on {data}", "sem_projeto": "No project", "prazo": "due {d}",
           "status": {"entrada": "Inbox", "a_fazer": "To do", "fazendo": "Doing", "esperando": "Waiting", "feito": "Done"},
           "importada": "Imported", "atualizada": "Updated by import",
           "prev_titulo": "# Import preview ({novas} new, {atualizadas} updated, {extras} days/archive/config/recurring docs, {conflitos} conflicts)",
           "prev_novas": "## New",
           "prev_atualizadas": "## Updated (same key; only title/status/due/priority/project/next step, arrays merged)",
           "prev_conflitos": "## Conflicts (not imported)",
           "prev_extras": "⚠️ The days/archive/config/recurring docs REPLACE the existing ones: use only on a new board.",
           "prev_indice": "Index: `update` indice/ativos with {p} (merge by id).",
           "conf_chave": "`{t}`: key {k} repeated in the file (only the first one is kept)",
           "conf_mesma": "`{t}` and `{o}` match the same task `{a}` (only the first one is kept)",
           "sem_titulo": "(untitled)"},
}


def txt(idioma):
    return TXT["pt" if str(idioma or "pt-BR").lower().startswith("pt") else "en"]


def sem_marcas(s):
    """NFD e sem nenhuma marca combinante (categorias Mn, Mc e Me), igual ao `.replace(/\\p{M}/gu, "")` da página."""
    return "".join(c for c in unicodedata.normalize("NFD", str(s or "")) if not unicodedata.category(c).startswith("M"))


def slug(s):
    s = sem_marcas(s).lower()
    return re.sub(r"[^a-z0-9:#@.]+", "-", s).strip("-")


def slug_projeto(s):
    """Slug de projeto/tag, igual ao `slug()` da página do quadro (SCHEMA § Slugs): NFD, sem marcas combinantes,
    minúsculas, e tudo que não é letra ou número de qualquer escrita (\\p{L}, \\p{N}) nem `:` vira `-`.
    `Gestão` → `gestao`; `项目` → `项目`; `Проект` → `проект`; `कागज` → `कगज` (marcas Mc também saem, como na página)."""
    s = sem_marcas(s).lower().strip()
    s = "".join(c if c == ":" or unicodedata.category(c)[0] in "LN" else "-" for c in s)
    return re.sub(r"-+", "-", s).strip("-")


def lista_projetos(v):
    """Lista de projetos sem vazios e sem repetir o mesmo slug (fica o primeiro nome; ordem preservada).
    Texto (coluna `projetos` do CSV) é uma lista JSON (`["A", "B"]`); texto que não é JSON vale como um nome só."""
    if isinstance(v, str):
        try:
            v = json.loads(v) if v.strip().startswith("[") else [v]
        except ValueError:
            v = [v]
    out, vistos = [], set()
    for x in v or []:
        x = str(x).strip()
        if x and slug_projeto(x) and slug_projeto(x) not in vistos:
            vistos.add(slug_projeto(x)); out.append(x)
    return out


def nome_projeto(s, nomes=None):
    """Nome de um projeto a partir do slug da tag: o `projeto` de outro card com esse slug; senão o slug capitalizado."""
    return (nomes or {}).get(s) or " ".join(w.capitalize() for w in s.split("-"))


def load_dir(d, colecao):
    out = {}
    for f in sorted(glob.glob(os.path.join(d, colecao, "*.json"))):
        out[os.path.basename(f)[:-5]] = json.load(open(f, encoding="utf-8"))
    return out


def normaliza(t, nomes=None):
    """Completa campos faltantes e corrige valores fora do contrato."""
    t = dict(t)
    t.setdefault("titulo", txt(IDIOMA)["sem_titulo"])
    if t.get("status") not in STATUS:
        t["status"] = "entrada"
    t.setdefault("prioridade", "media")
    for k in ["tags", "chaves", "relacionadas", "links", "conversas", "historico"]:
        t[k] = list(t.get(k) or [])
    for k in ["resolucao", "pai", "prazo", "concluido_em"]:
        t.setdefault(k, None)
    for k in ["projeto", "proximo_passo", "contexto", "resumo", "area"]:
        t[k] = t.get(k) or ""
    t.setdefault("fonte", {"tipo": "import", "ref": ""})
    t.setdefault("auto", False)
    t.setdefault("criado_em", NOW)
    t.setdefault("atualizado_em", t["criado_em"])
    t["historico"] = t["historico"][:50]
    legado = "projetos" not in t  # sem a lista: os outros projetos estão só nas tags (v2)
    ps = lista_projetos(t.get("projetos"))
    if t["projeto"]:
        ps = lista_projetos([t["projeto"]] + ps)  # o principal vai na frente
    if legado:
        ps = lista_projetos(ps + [nome_projeto(x[8:], nomes) for x in t["tags"] if str(x).startswith("projeto:") and x[8:]])
    t["projetos"] = ps
    t["projeto"] = t["projetos"][0] if t["projetos"] else ""
    for p in reversed(t["projetos"]):
        if "projeto:" + slug_projeto(p) not in t["tags"]:
            t["tags"].insert(0, "projeto:" + slug_projeto(p))
    return {k: t[k] for k in CAMPOS if k in t}


def cmd_export(a):
    pacote = {"formato": "quadro-tarefas", "versao": 1, "escopo": a.escopo, "exportado_em": NOW,
              "tasks": load_dir(a.dir, "tasks")}
    for col in COLECOES_CONFIG:
        pacote[col] = load_dir(a.dir, col)
    json.dump(pacote, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    nomes = {slug_projeto(t["projeto"]): t["projeto"] for t in pacote["tasks"].values() if t.get("projeto")}
    projs = {i: normaliza(t, nomes)["projetos"] for i, t in pacote["tasks"].items()}  # card v2: recupera os das tags
    rows = sorted(pacote["tasks"].items(), key=lambda kv: (kv[1].get("projeto") or "~", kv[1].get("status", "")))
    if a.csv:
        with open(a.csv, "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["id", "titulo", "status", "resolucao", "prioridade", "area", "projeto", "projetos", "tags", "chaves", "pai",
                        "prazo", "proximo_passo", "resumo", "criado_em", "atualizado_em", "concluido_em"])
            for i, t in rows:
                w.writerow([i, t.get("titulo"), t.get("status"), t.get("resolucao") or "", t.get("prioridade"), t.get("area"),
                            (projs[i] or [""])[0], json.dumps(projs[i], ensure_ascii=False), " ".join(t.get("tags") or []), " ".join(t.get("chaves") or []), t.get("pai") or "",
                            t.get("prazo") or "", t.get("proximo_passo"), t.get("resumo"), t.get("criado_em"),
                            t.get("atualizado_em"), t.get("concluido_em") or ""])
    if a.md:
        T = txt(a.idioma)
        linhas, atual = [T["md_titulo"].format(escopo=a.escopo, data=NOW[:10]), ""], None
        for i, t in rows:
            p = t.get("projeto") or T["sem_projeto"]
            if p != atual:
                linhas += ["", f"## {p}", ""]
                atual = p
            x = "x" if t.get("status") == "feito" else " "
            extra = " · ".join(filter(None, [T["status"].get(t.get("status"), t.get("status")), t.get("prazo") and T["prazo"].format(d=t["prazo"]),
                                             " ".join(t.get("tags") or [])]))
            linhas.append(f"- [{x}] **{t.get('titulo')}** ({extra})" + (f"\n  - → {t['proximo_passo']}" if t.get("proximo_passo") else ""))
        open(a.md, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    print(json.dumps({"tasks": len(pacote["tasks"]), "dias": len(pacote["dias"]), "arquivo": len(pacote["arquivo"]),
                      "recorrentes": len(pacote["recorrentes"]), "out": a.out, "csv": a.csv, "md": a.md}, ensure_ascii=False))


ID_OK = re.compile(r"^[A-Za-z0-9_~:@+-][A-Za-z0-9_.~:@+-]{0,119}$")
CAMPOS_IMPORT = ["titulo", "status", "resolucao", "prioridade", "prazo", "projeto", "proximo_passo"]  # escalares que o import pode atualizar
ARRAYS_UNIAO = ["chaves", "tags", "links", "projetos"]  # numa tarefa existente: unir com o que já existe (projetos: o principal da tarefa fica)


def _ascii_id(s):
    return slug(s).replace("/", "-").replace(".", "-")[:40].strip("-")


def id_seguro(raw, fallback):
    """Id de documento: sempre ASCII. Título só em outra escrita (`项目`) → `t-<hash curto do título>`."""
    i = str(raw or "")
    if not ID_OK.match(i) or i in (".", ".."):
        i = _ascii_id(i or fallback) or _ascii_id(fallback) or \
            "t-" + hashlib.sha1(str(fallback or raw or "").encode("utf-8")).hexdigest()[:8]
    return i


def dentro(base, nome):
    p = os.path.abspath(os.path.join(base, nome))
    if not p.startswith(os.path.abspath(base) + os.sep):
        sys.exit(f"caminho fora de {base}: {nome}")
    return p


def cmd_plan(a):
    T = txt(a.idioma)
    ent = json.load(open(a.entrada, encoding="utf-8"))
    if isinstance(ent, dict) and "tasks" in ent:
        brutos = [dict(t, id=i) for i, t in ent["tasks"].items()]
    else:
        brutos = list(ent)
    indice = json.load(open(a.indice, encoding="utf-8")).get("itens", {}) if a.indice and os.path.exists(a.indice) else {}
    vivos = {i: it for i, it in indice.items() if it.get("s") not in ("apagada", "arquivada")}
    por_chave = {k: i for i, it in vivos.items() for k in it.get("k", [])}
    ocupados = set(indice)  # ids apagados/arquivados também não são reaproveitados
    os.makedirs(a.saida, exist_ok=True)
    docs = os.path.join(a.saida, "docs")
    os.makedirs(docs, exist_ok=True)
    destinos, chaves_lote, conflitos = {}, {}, []
    mapa = {}  # id de origem -> id de destino (para remapear pai/relacionadas)
    planos = []
    nomes = {}  # slug -> nome do projeto, tirado dos próprios cards (para recuperar projetos que estão só nas tags)
    for b in brutos:
        if b.get("projeto"):
            nomes.setdefault(slug_projeto(b["projeto"]), str(b["projeto"]).strip())
    for n, bruto in enumerate(brutos):
        origem = str(bruto.get("id") or "")
        t = normaliza({k: v for k, v in bruto.items() if k != "id"}, nomes)
        alvo = next((por_chave[k] for k in t["chaves"] if k in por_chave), None)
        if not alvo and origem in vivos and not t["chaves"]:
            alvo = origem  # mesmo id e nenhuma chave dizendo o contrário
        repetida = next((k for k in t["chaves"] if k in chaves_lote), None)
        if repetida:
            conflitos.append(T["conf_chave"].format(t=t["titulo"], k=repetida))
            continue
        if alvo:
            if alvo in destinos:
                conflitos.append(T["conf_mesma"].format(t=t["titulo"], o=destinos[alvo], a=alvo))
                continue
            doc_id = alvo
        else:
            base = id_seguro(origem, t["titulo"])
            doc_id, k = base, 2
            while doc_id in ocupados or doc_id in destinos:
                doc_id = f"{base}-{k}"; k += 1
        destinos[doc_id] = t["titulo"]
        for k in t["chaves"]:
            chaves_lote[k] = doc_id
        if origem:
            mapa[origem] = doc_id
        planos.append((doc_id, bool(alvo), t))
    writes, novos, atualizados, idx = [], [], [], {}
    for doc_id, existe, t in planos:
        t["pai"] = mapa.get(t["pai"], t["pai"]) if t["pai"] else None
        t["relacionadas"] = [mapa.get(r, r) for r in t["relacionadas"]]
        p = dentro(docs, doc_id + ".json")
        if existe:
            # Atualização: só escalares importados + arrays para unir. Conversas, contexto, histórico e
            # ligações locais ficam como estão. A skill lê o doc atual, une os arrays, põe a linha no
            # histórico e manda `update` com o if_version lido (ver tarefas-io § Import).
            dados = {k: t[k] for k in CAMPOS_IMPORT if k != "projeto" and t.get(k) not in (None, "")}  # projeto vem por _unir.projetos
            dados["_unir"] = {k: t[k] for k in ARRAYS_UNIAO if t.get(k)}
            dados["_historico"] = T["atualizada"]
            json.dump(dados, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            writes.append({"op": "update", "collection": "tasks", "doc_id": doc_id, "file_path": p, "if_version": "PREENCHER"})
            atualizados.append((doc_id, t["titulo"]))
            # Prévia do índice com a união (a skill refaz a entrada a partir do card final, depois do merge).
            ent_i = dict(indice.get(doc_id, {}))
            ps = lista_projetos((ent_i.get("ps") or ([ent_i["p"]] if ent_i.get("p") else [])) + t["projetos"])
            uniao = lambda a, b: list(dict.fromkeys((a or []) + (b or [])))
            ent_i.update({"t": t["titulo"], "s": t["status"], "p": ps[0] if ps else "", "ps": ps,
                          "tags": uniao(ent_i.get("tags"), t["tags"]), "k": uniao(ent_i.get("k"), t["chaves"]), "u": NOW})
            idx[doc_id] = ent_i
        else:
            t["historico"] = ([{"em": NOW, "texto": T["importada"], "por": "io"}] + t["historico"])[:50]
            json.dump(t, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            writes.append({"op": "set", "collection": "tasks", "doc_id": doc_id, "file_path": p})
            novos.append((doc_id, t["titulo"]))
            idx[doc_id] = {"t": t["titulo"], "s": t["status"], "p": t["projeto"], "ps": t["projetos"], "tags": t["tags"], "k": t["chaves"],
                           "pai": t["pai"], "u": t["atualizado_em"]}
    extras = []
    if a.com_config and isinstance(ent, dict):
        # Só para quadro NOVO (quadro-tarefas). Em quadro existente, cada doc precisa do if_version lido.
        for col in COLECOES_CONFIG:
            for did, d in (ent.get(col) or {}).items():
                p = dentro(docs, f"_{col}-{id_seguro(did, col)}.json")
                json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                extras.append({"op": "set", "collection": col, "doc_id": id_seguro(did, col), "file_path": p, "so_quadro_novo": True})
    pi = os.path.abspath(os.path.join(a.saida, "indice-merge.json"))
    json.dump({"itens": idx, "atualizado_em": NOW}, open(pi, "w", encoding="utf-8"), ensure_ascii=False)
    todos = writes + extras
    lotes = [todos[i:i + 45] for i in range(0, len(todos), 45)] or [[]]
    for n, lote in enumerate(lotes, 1):
        json.dump(lote, open(os.path.join(a.saida, f"writes-{n}.json"), "w", encoding="utf-8"), ensure_ascii=False)
    prev = [T["prev_titulo"].format(novas=len(novos), atualizadas=len(atualizados), extras=len(extras), conflitos=len(conflitos)), ""]
    prev += [T["prev_novas"]] + [f"- {t} `{i}`" for i, t in novos] + ["", T["prev_atualizadas"]]
    prev += [f"- {t} `{i}`" for i, t in atualizados]
    if conflitos:
        prev += ["", T["prev_conflitos"]] + [f"- {c}" for c in conflitos]
    if extras:
        prev += ["", T["prev_extras"]]
    prev += ["", T["prev_indice"].format(p=pi)]
    open(os.path.join(a.saida, "preview.md"), "w", encoding="utf-8").write("\n".join(prev) + "\n")
    print(json.dumps({"novas": len(novos), "atualizadas": len(atualizados), "extras": len(extras), "conflitos": len(conflitos),
                      "lotes": len(lotes), "preview": os.path.join(a.saida, "preview.md"), "indice": pi}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("export"); e.add_argument("--dir", required=True); e.add_argument("--escopo", required=True)
    e.add_argument("--out", required=True); e.add_argument("--csv"); e.add_argument("--md")
    e.add_argument("--idioma", default="pt-BR", help="config/preferencias.idioma (pt* = português, outro = inglês)")
    p = sp.add_parser("plan"); p.add_argument("--entrada", required=True); p.add_argument("--indice")
    p.add_argument("--saida", required=True); p.add_argument("--com-config", action="store_true")
    p.add_argument("--idioma", default="pt-BR", help="config/preferencias.idioma (pt* = português, outro = inglês)")
    a = ap.parse_args()
    global IDIOMA
    IDIOMA = a.idioma
    {"export": cmd_export, "plan": cmd_plan}[a.cmd](a)


if __name__ == "__main__":
    main()

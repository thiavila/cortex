#!/usr/bin/env python3
"""Import/export do quadro de tarefas (modelo v1, ver SCHEMA.md).

export: junta os documentos baixados com `ArtifactData list ... out_dir=<dir>` num pacote.
  python3 io.py export --dir <out_dir> --escopo pessoal --out pacote.json [--csv x.csv] [--md x.md]

plan: compara um pacote (ou uma lista de tarefas vinda de outro sistema, já no formato v1)
  com o índice atual e gera os arquivos de escrita + uma prévia legível.
  python3 io.py plan --entrada pacote.json --indice indice.json --saida <dir> [--com-config]
  -> <dir>/preview.md, <dir>/writes-N.json (lotes de até 45 escritas, com file_path absolutos)

Casamento: mesma chave externa (`chaves`) = mesma tarefa (atualiza); senão, mesmo id; senão, nova.
"""
import argparse, csv, datetime as dt, glob, json, os, re, sys, unicodedata

NOW = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")
CAMPOS = ["titulo", "status", "resolucao", "prioridade", "area", "projeto", "projetos", "tags", "chaves", "pai", "relacionadas",
          "prazo", "proximo_passo", "contexto", "resumo", "links", "conversas", "historico", "fonte", "auto",
          "criado_em", "atualizado_em", "concluido_em"]
STATUS = {"entrada", "a_fazer", "fazendo", "esperando", "feito"}


def slug(s):
    s = unicodedata.normalize("NFD", str(s or ""))
    s = "".join(c for c in s if unicodedata.category(c) != "Mn").lower()
    return re.sub(r"[^a-z0-9:#@.]+", "-", s).strip("-")


def slug_projeto(s):
    """Slug de projeto/tag, igual ao `slug()` da página do quadro (só a-z, 0-9 e ":")."""
    s = unicodedata.normalize("NFD", str(s or ""))
    s = re.sub("[\u0300-\u036f]", "", s).lower().strip()  # mesma faixa do JS
    return re.sub(r"[^a-z0-9:]+", "-", s).strip("-")


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
    t.setdefault("titulo", "(sem título)")
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
              "tasks": load_dir(a.dir, "tasks"), "dias": load_dir(a.dir, "dias"),
              "arquivo": load_dir(a.dir, "arquivo"), "config": load_dir(a.dir, "config")}
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
        linhas, atual = [f"# Quadro {a.escopo} — exportado em {NOW[:10]}", ""], None
        for i, t in rows:
            p = t.get("projeto") or "Sem projeto"
            if p != atual:
                linhas += ["", f"## {p}", ""]
                atual = p
            x = "x" if t.get("status") == "feito" else " "
            extra = " · ".join(filter(None, [t.get("status"), t.get("prazo") and "prazo " + t["prazo"],
                                             " ".join(t.get("tags") or [])]))
            linhas.append(f"- [{x}] **{t.get('titulo')}** ({extra})" + (f"\n  - → {t['proximo_passo']}" if t.get("proximo_passo") else ""))
        open(a.md, "w", encoding="utf-8").write("\n".join(linhas) + "\n")
    print(json.dumps({"tasks": len(pacote["tasks"]), "dias": len(pacote["dias"]), "arquivo": len(pacote["arquivo"]),
                      "out": a.out, "csv": a.csv, "md": a.md}, ensure_ascii=False))


ID_OK = re.compile(r"^[A-Za-z0-9_~:@+-][A-Za-z0-9_.~:@+-]{0,119}$")
CAMPOS_IMPORT = ["titulo", "status", "resolucao", "prioridade", "prazo", "projeto", "proximo_passo"]  # escalares que o import pode atualizar
ARRAYS_UNIAO = ["chaves", "tags", "links", "projetos"]  # numa tarefa existente: unir com o que já existe (projetos: o principal da tarefa fica)


def id_seguro(raw, fallback):
    i = str(raw or "")
    if not ID_OK.match(i) or i in (".", ".."):
        i = slug(i or fallback).replace("/", "-").replace(".", "-")[:40].strip("-") or "tarefa"
    return i


def dentro(base, nome):
    p = os.path.abspath(os.path.join(base, nome))
    if not p.startswith(os.path.abspath(base) + os.sep):
        sys.exit(f"caminho fora de {base}: {nome}")
    return p


def cmd_plan(a):
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
            conflitos.append(f"`{t['titulo']}`: chave {repetida} repetida no arquivo (fica só a primeira)")
            continue
        if alvo:
            if alvo in destinos:
                conflitos.append(f"`{t['titulo']}` e `{destinos[alvo]}` casam com a mesma tarefa `{alvo}` (fica só a primeira)")
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
            dados["_historico"] = "Atualizada por import"
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
            t["historico"] = ([{"em": NOW, "texto": "Importada", "por": "io"}] + t["historico"])[:50]
            json.dump(t, open(p, "w", encoding="utf-8"), ensure_ascii=False)
            writes.append({"op": "set", "collection": "tasks", "doc_id": doc_id, "file_path": p})
            novos.append((doc_id, t["titulo"]))
            idx[doc_id] = {"t": t["titulo"], "s": t["status"], "p": t["projeto"], "ps": t["projetos"], "tags": t["tags"], "k": t["chaves"],
                           "pai": t["pai"], "u": t["atualizado_em"]}
    extras = []
    if a.com_config and isinstance(ent, dict):
        # Só para quadro NOVO (quadro-tarefas). Em quadro existente, cada doc precisa do if_version lido.
        for col in ["dias", "arquivo", "config"]:
            for did, d in (ent.get(col) or {}).items():
                p = dentro(docs, f"_{col}-{id_seguro(did, col)}.json")
                json.dump(d, open(p, "w", encoding="utf-8"), ensure_ascii=False)
                extras.append({"op": "set", "collection": col, "doc_id": id_seguro(did, col), "file_path": p, "so_quadro_novo": True})
    pi = os.path.abspath(os.path.join(a.saida, "indice-merge.json"))
    json.dump({"itens": idx, "atualizado_em": NOW}, open(pi, "w", encoding="utf-8"), ensure_ascii=False)
    todos = writes + extras
    lotes = [todos[i:i + 45] for i in range(0, len(todos), 45)] or [[]]
    for n, lote in enumerate(lotes, 1):
        json.dump(lote, open(os.path.join(a.saida, f"writes-{n}.json"), "w"), ensure_ascii=False)
    prev = [f"# Prévia do import ({len(novos)} novas, {len(atualizados)} atualizadas, {len(extras)} docs de dias/arquivo/config, {len(conflitos)} conflitos)", ""]
    prev += ["## Novas"] + [f"- {t} `{i}`" for i, t in novos] + ["", "## Atualizadas (mesma chave; só título/status/prazo/prioridade/projeto/próximo passo, arrays unidos)"]
    prev += [f"- {t} `{i}`" for i, t in atualizados]
    if conflitos:
        prev += ["", "## Conflitos (não entram)"] + [f"- {c}" for c in conflitos]
    if extras:
        prev += ["", "⚠️ Os docs de dias/arquivo/config SUBSTITUEM os existentes: use só em quadro novo."]
    prev += ["", f"Índice: `update` em indice/ativos com {pi} (merge por id)."]
    open(os.path.join(a.saida, "preview.md"), "w", encoding="utf-8").write("\n".join(prev) + "\n")
    print(json.dumps({"novas": len(novos), "atualizadas": len(atualizados), "extras": len(extras), "conflitos": len(conflitos),
                      "lotes": len(lotes), "preview": os.path.join(a.saida, "preview.md"), "indice": pi}, ensure_ascii=False))


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    e = sp.add_parser("export"); e.add_argument("--dir", required=True); e.add_argument("--escopo", required=True)
    e.add_argument("--out", required=True); e.add_argument("--csv"); e.add_argument("--md")
    p = sp.add_parser("plan"); p.add_argument("--entrada", required=True); p.add_argument("--indice")
    p.add_argument("--saida", required=True); p.add_argument("--com-config", action="store_true")
    a = ap.parse_args()
    {"export": cmd_export, "plan": cmd_plan}[a.cmd](a)


if __name__ == "__main__":
    main()

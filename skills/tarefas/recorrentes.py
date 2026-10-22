#!/usr/bin/env python3
"""Tarefas recorrentes: quais ocorrências já chegaram e viram card. Mesma regra da página (board-src.html § Recorrentes).

Uso: python3 recorrentes.py --dir <pasta com recorrentes/*.json> --indice <indice.json> [--hoje AAAA-MM-DD] --saida <plano.json>
Saída: lista de {rid, ocorrencia, puladas, acao: "criar"|"anotar", id, tarefa (corpo do card, só em criar), aberta}.
Quem chama grava: set do card (conferindo antes que o id está livre), update recorrentes/<rid> {ultima} e o índice.
"""
import argparse, calendar, datetime as dt, glob, json, os

D = dt.date.fromisoformat
def iso_dow(d): return d.isoweekday()
def inicio(r): return D((r.get("regra") or {}).get("inicio") or (r.get("criado_em") or "")[:10] or dt.date.today().isoformat())

def casa(r, d):
    g, ini = r.get("regra") or {}, inicio(r)
    n = max(1, int(g.get("a_cada") or 1))
    if d < ini: return False
    t = g.get("tipo")
    if t == "diaria": return (d - ini).days % n == 0
    if t == "semanal":
        dias = g.get("dias") or [iso_dow(ini)]
        if iso_dow(d) not in dias: return False
        seg = lambda x: x - dt.timedelta(days=iso_dow(x) - 1)
        return round((seg(d) - seg(ini)).days / 7) % n == 0
    if t == "mensal":
        if ((d.year - ini.year) * 12 + d.month - ini.month) % n: return False
        ult = calendar.monthrange(d.year, d.month)[1]
        dia = int(g.get("dia") or ini.day)
        return d.day == (ult if dia == -1 else min(dia, ult))
    return False

def proxima(r, de):
    d = max(de, inicio(r))
    for _ in range(800):
        if casa(r, d): return d
        d += dt.timedelta(days=1)
    return None

def regra_txt(r):
    g = r.get("regra") or {}; n = max(1, int(g.get("a_cada") or 1)); dow = ["", "seg", "ter", "qua", "qui", "sex", "sáb", "dom"]
    if g.get("tipo") == "diaria": return "todo dia" if n == 1 else f"a cada {n} dias"
    if g.get("tipo") == "semanal": return ("toda semana" if n == 1 else f"a cada {n} semanas") + " · " + ", ".join(dow[x] for x in (g.get("dias") or [iso_dow(inicio(r))]))
    if g.get("tipo") == "mensal": return ("todo mês" if n == 1 else f"a cada {n} meses") + " · dia " + ("último" if int(g.get("dia") or 0) == -1 else str(g.get("dia") or inicio(r).day))
    return "regra inválida"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--indice", required=True)
    ap.add_argument("--hoje"); ap.add_argument("--saida", required=True)
    a = ap.parse_args()
    hoje = D(a.hoje) if a.hoje else dt.date.today()
    itens = json.load(open(a.indice, encoding="utf-8")).get("itens", {}) if os.path.exists(a.indice) else {}
    pasta = os.path.join(a.dir, "recorrentes") if os.path.isdir(os.path.join(a.dir, "recorrentes")) else a.dir
    plano = []
    for f in sorted(glob.glob(os.path.join(pasta, "*.json"))):
        rid = os.path.basename(f)[:-5]; r = json.load(open(f, encoding="utf-8"))
        if r.get("ativo") is False: continue
        limite = hoje + dt.timedelta(days=max(0, int(r.get("antecedencia_dias") or 0)))
        s = proxima(r, D(r["ultima"]) + dt.timedelta(days=1) if r.get("ultima") else inicio(r)); alvo, n = None, 0
        while s and s <= limite:
            alvo, n = s, n + 1; s = proxima(r, s + dt.timedelta(days=1))
        if not alvo: continue
        aberta = next((i for i, x in itens.items() if f"recorrente:{rid}" in (x.get("tags") or []) and x.get("s") not in ("feito", "apagada", "arquivada")), None)
        item = {"rid": rid, "ocorrencia": alvo.isoformat(), "puladas": n - 1, "aberta": aberta}
        if aberta:
            item["acao"] = "anotar"
        else:
            tid = f"{rid}--{alvo.isoformat()}"[:60]
            item.update(acao="criar", id=tid, tarefa={
                "titulo": r.get("titulo"), "status": "a_fazer", "resolucao": None, "prioridade": r.get("prioridade") or "media",
                "area": r.get("area") or "geral", "projeto": r.get("projeto") or "", "projetos": [r["projeto"]] if r.get("projeto") else [],
                "tags": sorted(set((r.get("tags") or []) + [f"recorrente:{rid}"])), "chaves": [f"recorrente:{rid}@{alvo.isoformat()}"],
                "pai": None, "relacionadas": [], "prazo": alvo.isoformat(), "proximo_passo": r.get("proximo_passo") or "",
                "contexto": r.get("contexto") or "", "resumo": "", "links": r.get("links") or [], "conversas": [], "recorrente": rid,
                "historico": [{"texto": f"Ocorrência de {alvo:%d/%m} da recorrente ({regra_txt(r)})" + (f"; {n-1} anterior(es) passaram sem card" if n > 1 else ""), "por": "bom-dia"}],
                "fonte": {"tipo": "recorrente", "ref": rid}, "auto": True, "concluido_em": None})
        plano.append(item)
    json.dump(plano, open(a.saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(plano)} recorrente(s) com ocorrência: " + ", ".join(f"{p['rid']}@{p['ocorrencia']}({p['acao']})" for p in plano))

if __name__ == "__main__":
    main()

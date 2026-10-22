#!/usr/bin/env python3
"""Tarefas recorrentes: quais ocorrências já chegaram e viram card. Mesma regra da página (board-src.html § Recorrentes).

Uso: sh <skills>/tarefas/py recorrentes.py --dir <pasta com recorrentes/*.json> --indice <indice.json> --saida <plano.json>
       [--hoje AAAA-MM-DD] [--fuso <IANA>] [--idioma pt-BR|en|…] [--locale <BCP-47>] [--area-padrao <id>]
--hoje: sem ele, hoje no --fuso (config/preferencias.fuso; sem fuso = o do sistema).
--idioma/--locale: língua do texto gravado no histórico (pt* = português, outro = inglês) e formato da data nele
                   (locale terminado em -US = mês/dia, os outros = dia/mês). --area-padrao: config/preferencias.area_padrao.
Saída: lista de {rid, ocorrencia, puladas, acao: "criar"|"anotar", id, tarefa (corpo do card, só em criar), aberta}.
Quem chama grava: set do card (conferindo antes que o id está livre), update recorrentes/<rid> {ultima} e o índice.
"""
import argparse, calendar, datetime as dt, glob, json, os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos  # noqa: E402

TXT = {
    "pt": {"dow": ["", "seg", "ter", "qua", "qui", "sex", "sáb", "dom"], "dia1": "todo dia", "diaN": "a cada {n} dias",
           "sem1": "toda semana", "semN": "a cada {n} semanas", "mes1": "todo mês", "mesN": "a cada {n} meses",
           "dia": "dia {d}", "ultimo": "dia último", "invalida": "regra inválida",
           "hist": "Ocorrência de {data} da recorrente ({regra})", "puladas": "; {n} anterior(es) passaram sem card"},
    "en": {"dow": ["", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"], "dia1": "every day", "diaN": "every {n} days",
           "sem1": "every week", "semN": "every {n} weeks", "mes1": "every month", "mesN": "every {n} months",
           "dia": "day {d}", "ultimo": "last day", "invalida": "invalid rule",
           "hist": "Occurrence of {data} of the recurring task ({regra})", "puladas": "; {n} earlier one(s) passed without a card"},
}


def txt(idioma):
    return TXT["pt" if str(idioma or "").lower().startswith("pt") else "en"]


def data_curta(d, locale):
    """Data sem ano: mês/dia nos locales -US, dia/mês nos outros."""
    return f"{d:%m/%d}" if str(locale or "").upper().endswith("-US") else f"{d:%d/%m}"

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

def regra_txt(r, idioma="pt-BR"):
    T = txt(idioma); g = r.get("regra") or {}; n = max(1, int(g.get("a_cada") or 1)); dow = T["dow"]
    if g.get("tipo") == "diaria": return T["dia1"] if n == 1 else T["diaN"].format(n=n)
    if g.get("tipo") == "semanal": return (T["sem1"] if n == 1 else T["semN"].format(n=n)) + " · " + ", ".join(dow[x] for x in (g.get("dias") or [iso_dow(inicio(r))]))
    if g.get("tipo") == "mensal": return (T["mes1"] if n == 1 else T["mesN"].format(n=n)) + " · " + (T["ultimo"] if int(g.get("dia") or 0) == -1 else T["dia"].format(d=g.get("dia") or inicio(r).day))
    return T["invalida"]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", required=True); ap.add_argument("--indice", required=True)
    ap.add_argument("--hoje"); ap.add_argument("--saida", required=True)
    ap.add_argument("--fuso", help="IANA do quadro (config/preferencias.fuso); sem ele, o do sistema")
    ap.add_argument("--idioma", default="pt-BR"); ap.add_argument("--locale")
    ap.add_argument("--area-padrao", default="", help="config/preferencias.area_padrao (sem ela, a primeira área)")
    a = ap.parse_args()
    hoje = D(a.hoje) if a.hoje else caminhos.hoje(caminhos.fuso(a.fuso))
    T, loc = txt(a.idioma), a.locale or a.idioma
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
                "area": r.get("area") or a.area_padrao or "", "projeto": r.get("projeto") or "", "projetos": [r["projeto"]] if r.get("projeto") else [],
                "tags": sorted(set((r.get("tags") or []) + [f"recorrente:{rid}"])), "chaves": [f"recorrente:{rid}@{alvo.isoformat()}"],
                "pai": None, "relacionadas": [], "prazo": alvo.isoformat(), "proximo_passo": r.get("proximo_passo") or "",
                "contexto": r.get("contexto") or "", "resumo": "", "links": r.get("links") or [], "conversas": [], "recorrente": rid,
                "historico": [{"texto": T["hist"].format(data=data_curta(alvo, loc), regra=regra_txt(r, a.idioma)) + (T["puladas"].format(n=n - 1) if n > 1 else ""), "por": "bom-dia"}],
                "fonte": {"tipo": "recorrente", "ref": rid}, "auto": True, "concluido_em": None})
        plano.append(item)
    json.dump(plano, open(a.saida, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"{len(plano)} recorrente(s) com ocorrência: " + ", ".join(f"{p['rid']}@{p['ocorrencia']}({p['acao']})" for p in plano))

if __name__ == "__main__":
    main()

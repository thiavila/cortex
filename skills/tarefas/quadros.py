#!/usr/bin/env python3
"""Atalho local dos quadros de tarefas já vistos nesta máquina.

Não é fonte de verdade: só evita procurar na lista de artefatos toda vez. Guarda URLs de qualquer conta;
quem decide qual é o quadro da sessão é a resposta do ArtifactData (ver ACHAR-QUADRO.md).

Só entram quadros confirmados na lista de artefatos da própria conta ("mine"): quadro compartilhado por
outra pessoa não vai para cá (ver ACHAR-QUADRO.md).

Uso:
  python3 quadros.py listar                          # uma URL por linha, mais recente primeiro
  python3 quadros.py lembrar --url <url> --titulo "<título>"
  python3 quadros.py esquecer --url <url>
"""
import argparse, datetime as dt, fcntl, json, os, re, tempfile

ARQ = os.path.expanduser(os.environ.get("QUADROS_ARQ", "~/.claude/tarefas/quadros.json"))
URL_OK = re.compile(r"^https://claude\.ai/(code/)?artifact/[A-Za-z0-9_-]+$")


def ler():
    try:
        d = json.load(open(ARQ))
        return [q for q in d.get("quadros", []) if URL_OK.match(q.get("url", ""))]
    except Exception:
        return []


def gravar(qs):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(ARQ), prefix=".quadros-")
    with os.fdopen(fd, "w") as f:
        json.dump({"quadros": qs}, f, ensure_ascii=False, indent=2)
    os.replace(tmp, ARQ)


p = argparse.ArgumentParser()
sp = p.add_subparsers(dest="cmd", required=True)
sp.add_parser("listar")
l = sp.add_parser("lembrar"); l.add_argument("--url", required=True); l.add_argument("--titulo", default="")
e = sp.add_parser("esquecer"); e.add_argument("--url", required=True)
a = p.parse_args()

os.makedirs(os.path.dirname(ARQ), exist_ok=True)
trava = open(ARQ + ".lock", "w")
fcntl.flock(trava, fcntl.LOCK_EX)  # ler → alterar → gravar sem atropelar outra sessão
qs = ler()
if a.cmd == "listar":
    for q in sorted(qs, key=lambda q: q.get("visto_em", ""), reverse=True):
        print(q["url"])
elif a.cmd == "lembrar":
    if not URL_OK.match(a.url):
        raise SystemExit("URL de artefato inválida")
    agora = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    qs = [q for q in qs if q["url"] != a.url] + [{"url": a.url, "titulo": a.titulo, "visto_em": agora}]
    gravar(qs)
elif a.cmd == "esquecer":
    gravar([q for q in qs if q["url"] != a.url])

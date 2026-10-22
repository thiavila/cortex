#!/usr/bin/env python3
"""Atalho local dos quadros de tarefas já vistos nesta máquina.

Não é fonte de verdade: só evita procurar na lista de artefatos toda vez. Guarda URLs de qualquer conta;
quem decide qual é o quadro da sessão é a resposta do ArtifactData (ver ACHAR-QUADRO.md).

Só entram quadros confirmados na lista de artefatos da própria conta ("mine"): quadro compartilhado por
outra pessoa não vai para cá (ver ACHAR-QUADRO.md).

Arquivo: $QUADROS_ARQ, senão <dados>/tarefas/quadros.json (<dados>: ver caminhos.py). O de antes da v0.3
(~/.claude/tarefas/quadros.json), se for outro e existir, ainda entra no `listar` até a primeira gravação, que
copia as URLs dele para o arquivo novo (o antigo não é alterado).

Uso:
  sh <skills>/tarefas/py quadros.py listar                          # uma URL por linha, mais recente primeiro
  sh <skills>/tarefas/py quadros.py lembrar --url <url> --titulo "<título>"
  sh <skills>/tarefas/py quadros.py esquecer --url <url>
"""
import argparse
import contextlib
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos  # noqa: E402

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # macOS/Linux
    msvcrt = None

URL_OK = re.compile(r"^https://claude\.ai/(code/)?artifact/[A-Za-z0-9_-]+$")
ESPERA = 15      # segundos esperando a trava antes de desistir
VELHA = 60       # trava em arquivo (O_EXCL) mais velha que isso = sobra de processo morto


def arquivo():
    if os.environ.get("QUADROS_ARQ"):
        return os.path.abspath(os.path.expanduser(os.environ["QUADROS_ARQ"]))
    return os.path.join(caminhos.dados(), "tarefas", "quadros.json")


def arquivo_legado(arq):
    """O arquivo de antes da v0.3, se for outro (e só quando QUADROS_ARQ não fixa o arquivo)."""
    if os.environ.get("QUADROS_ARQ"):
        return None
    leg = os.path.join(caminhos.legado(), "tarefas", "quadros.json")
    if os.path.normcase(os.path.realpath(leg)) == os.path.normcase(os.path.realpath(arq)) or not os.path.exists(leg):
        return None
    return leg


@contextlib.contextmanager
def trava(caminho):
    """Trava exclusiva entre processos: fcntl (macOS/Linux), msvcrt (Windows), senão arquivo criado com O_EXCL."""
    if fcntl is not None:
        with open(caminho, "a+") as f:
            fcntl.flock(f, fcntl.LOCK_EX)
            try:
                yield
            finally:
                fcntl.flock(f, fcntl.LOCK_UN)
        return
    if msvcrt is not None:
        with open(caminho, "a+") as f:
            f.seek(0)
            fim = time.time() + ESPERA
            while True:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.time() > fim:
                        raise SystemExit(f"trava ocupada há {ESPERA}s: {caminho}")
                    time.sleep(0.05)
            try:
                yield
            finally:
                f.seek(0)
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
                except OSError:
                    pass
        return
    excl = caminho + ".excl"
    fim = time.time() + ESPERA
    while True:
        try:
            fd = os.open(excl, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(excl) > VELHA:
                    os.remove(excl)  # sobra de um processo que morreu segurando a trava
                    continue
            except OSError:
                continue
            if time.time() > fim:
                raise SystemExit(f"trava ocupada há {ESPERA}s: {excl}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.remove(excl)
        except OSError:
            pass


def _ler_arq(p):
    try:
        with open(p, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _validos(d):
    return [q for q in (d.get("quadros") or []) if isinstance(q, dict) and URL_OK.match(q.get("url", ""))]


def ler(arq):
    """Quadros do arquivo; mais os do arquivo antigo enquanto o novo não os tiver copiado."""
    d = _ler_arq(arq)
    qs = _validos(d)
    leg = arquivo_legado(arq)
    if leg and not d.get("legado_copiado"):
        urls = {q["url"] for q in qs}
        qs += [q for q in _validos(_ler_arq(leg)) if q["url"] not in urls]
    return qs


def gravar(arq, qs):
    d = {"quadros": qs}
    if arquivo_legado(arq):
        d["legado_copiado"] = True  # a lista acima já tem as URLs do arquivo antigo
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(arq), prefix=".quadros-")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        json.dump(d, f, ensure_ascii=False, indent=2)
    os.replace(tmp, arq)


def main(argv=None):
    p = argparse.ArgumentParser()
    sp = p.add_subparsers(dest="cmd", required=True)
    sp.add_parser("listar")
    l = sp.add_parser("lembrar"); l.add_argument("--url", required=True); l.add_argument("--titulo", default="")
    e = sp.add_parser("esquecer"); e.add_argument("--url", required=True)
    a = p.parse_args(argv)

    arq = arquivo()
    os.makedirs(os.path.dirname(arq), exist_ok=True)
    with trava(arq + ".lock"):  # ler → alterar → gravar sem atropelar outra sessão
        qs = ler(arq)
        if a.cmd == "listar":
            for q in sorted(qs, key=lambda q: q.get("visto_em", ""), reverse=True):
                print(q["url"])
        elif a.cmd == "lembrar":
            if not URL_OK.match(a.url):
                raise SystemExit("URL de artefato inválida")
            agora = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
            gravar(arq, [q for q in qs if q["url"] != a.url] + [{"url": a.url, "titulo": a.titulo, "visto_em": agora}])
        elif a.cmd == "esquecer":
            gravar(arq, [q for q in qs if q["url"] != a.url])


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Caminhos locais do Cortex, iguais em macOS, Windows e Linux (Python 3.8+, só biblioteca padrão).

Importável (`import caminhos`) e de linha de comando:
  sh <skills>/tarefas/py <skills>/tarefas/caminhos.py           # imprime <dados>
  sh <skills>/tarefas/py <skills>/tarefas/caminhos.py --tudo    # JSON com tudo o que está abaixo

- dados()           pasta de estado local do Cortex: $CORTEX_DADOS, senão $CLAUDE_CONFIG_DIR, senão ~/.claude
                    (SCHEMA.md § `<dados>`). $CLAUDE_PLUGIN_DATA fica de fora de propósito: no shell das skills ele
                    pode vir de OUTRO plugin (o Claude Code exporta o do último hook que rodou), e o hook e os scripts
                    precisam cair na mesma pasta.
- pastas_projects() pastas de transcritos do Claude Code que existem: <CLAUDE_CONFIG_DIR>/projects e ~/.claude/projects
                    (a da conta ativa primeiro, sem repetir). $CORTEX_PROJETOS (pastas separadas por os.pathsep:
                    `:` no macOS/Linux, `;` no Windows) substitui essa lista: só as que existirem, e nada mais.
- so()              darwin | windows | linux (env CORTEX_SO força um deles, para testes).
- pastas_app()      pastas do app desktop do Claude que têm `claude-code-sessions` (a do app desta sessão primeiro).
- fuso(nome) / agora(tz) / no_fuso(iso, tz): datas no fuso IANA do quadro; sem zoneinfo (3.8) ou sem a base de
                    fusos (Windows sem o pacote tzdata) cai na hora local do sistema, com aviso no stderr.
"""
import datetime as dt
import glob
import json
import os
import re
import sys

LEGADO = "~/.claude"  # onde o Cortex guardava tudo até a v0.2


def _exp(p):
    return os.path.abspath(os.path.expanduser(p))


def dados():
    for v in (os.environ.get("CORTEX_DADOS"), os.environ.get("CLAUDE_CONFIG_DIR")):
        if v and v.strip():
            return _exp(v.strip())
    return _exp(LEGADO)


def legado():
    """A pasta de estado de antes da v0.3 (~/.claude), para ler o que ficou lá."""
    return _exp(LEGADO)


def pastas_projects():
    extra = os.environ.get("CORTEX_PROJETOS")
    if extra is not None and extra.strip():  # override (testes): só estas, e só as que existem
        out = []
        for d in extra.split(os.pathsep):
            p = _exp(d.strip()) if d.strip() else ""
            if p and os.path.isdir(p) and os.path.normcase(p) not in [os.path.normcase(x) for x in out]:
                out.append(p)
        return out
    out = []
    for d in (os.environ.get("CLAUDE_CONFIG_DIR"), LEGADO):
        if not d or not d.strip():
            continue
        p = os.path.join(_exp(d.strip()), "projects")
        if os.path.isdir(p) and os.path.normcase(p) not in [os.path.normcase(x) for x in out]:
            out.append(p)
    return out


def so():
    f = (os.environ.get("CORTEX_SO") or "").strip().lower()
    if f in ("darwin", "windows", "linux"):
        return f
    if sys.platform == "darwin":
        return "darwin"
    if sys.platform.startswith(("win", "cygwin", "msys")):
        return "windows"
    return "linux"


# Onde o app desktop guarda as coisas dele, por SO. O nome da pasta do app pode ter sufixo (ex.: um sufixo por conta ou perfil).
_EXEC_APP = {
    "darwin": r"(.*[\\/]Application Support[\\/][^\\/]+)[\\/]",
    "windows": r"(.*[\\/]AppData[\\/](?:Roaming|Local)[\\/][^\\/]+)[\\/]",
    "linux": r"(.*[\\/]\.config[\\/][^\\/]+)[\\/]",
}


def _bases_app(s):
    if s == "darwin":
        return [_exp("~/Library/Application Support")]
    if s == "windows":
        return [os.environ[k] for k in ("APPDATA", "LOCALAPPDATA") if os.environ.get(k)]
    return [_exp(os.environ.get("XDG_CONFIG_HOME") or "~/.config")]


def pastas_app():
    """Pastas do app desktop do Claude com `claude-code-sessions` dentro. A do app que rodou esta sessão
    (tirada de CLAUDE_CODE_EXECPATH) vem primeiro; depois as outras `Claude*` da pasta de apps do SO."""
    s, out = so(), []

    def add(p):
        if p and os.path.isdir(os.path.join(p, "claude-code-sessions")):
            p = os.path.abspath(p)
            if os.path.normcase(p) not in [os.path.normcase(x) for x in out]:
                out.append(p)

    m = re.search(_EXEC_APP[s], os.environ.get("CLAUDE_CODE_EXECPATH", ""))
    if m:
        add(m.group(1))
    for base in _bases_app(s):
        for p in sorted(glob.glob(os.path.join(base, "Claude*"))):
            add(p)
    return out


# --- fuso -------------------------------------------------------------------------------------------------------

def _aviso(msg):
    print(msg, file=sys.stderr)


def fuso(nome=None):
    """tzinfo do fuso IANA `nome`. Vazio → None (= hora local do sistema). Sem zoneinfo/tzdata → None com aviso."""
    if not nome:
        return None
    if nome.upper() in ("UTC", "ETC/UTC", "Z"):
        return dt.timezone.utc
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError:
        _aviso(f"aviso: Python sem zoneinfo; usando a hora local do sistema no lugar de {nome} "
               f"(warning: no zoneinfo, using system local time instead of {nome})")
        return None
    try:
        return ZoneInfo(nome)
    except Exception:
        _aviso(f"aviso: fuso {nome} indisponível (no Windows, instale o pacote tzdata); usando a hora local "
               f"(warning: time zone {nome} unavailable, using system local time)")
        return None


def agora(tz=None):
    """Agora, com fuso: no `tz`, ou no local do sistema."""
    return dt.datetime.now(tz) if tz else dt.datetime.now().astimezone()


def hoje(tz=None):
    return agora(tz).date()


def no_fuso(iso, tz=None):
    """Timestamp ISO (`2026-10-22T01:30:00.123Z`, com ou sem fuso; sem fuso = UTC) → datetime no `tz` (ou local)."""
    if not iso:
        return None
    s = str(iso).strip()
    m = re.match(r"^(\d{4}-\d{2}-\d{2})[T ](\d{2}:\d{2}(?::\d{2})?)(?:\.\d+)?(Z|[+-]\d{2}:?\d{2})?$", s)
    if not m:
        return None
    hora = m.group(2) if len(m.group(2)) > 5 else m.group(2) + ":00"
    z = m.group(3) or "+00:00"
    if z == "Z":
        z = "+00:00"
    elif ":" not in z:
        z = z[:3] + ":" + z[3:]
    try:
        d = dt.datetime.fromisoformat(f"{m.group(1)}T{hora}{z}")
    except ValueError:
        return None
    return d.astimezone(tz) if tz else d.astimezone()


def tudo():
    return {"dados": dados(), "legado": legado(), "pastas_projects": pastas_projects(), "so": so(),
            "pastas_app": pastas_app()}


if __name__ == "__main__":
    if "--tudo" in sys.argv[1:]:
        print(json.dumps(tudo(), ensure_ascii=False, indent=1))
    else:
        print(dados())

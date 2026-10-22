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
- fuso(nome) / agora(tz) / no_fuso(iso, tz): datas no fuso IANA do quadro. Sem nome = hora local do sistema. Nome
                    pedido que não carrega (Python 3.8 sem zoneinfo, Windows sem o pacote tzdata, nome errado) é erro:
                    uma linha no stderr e ErroFuso (um SystemExit com código 3), a não ser que seja o próprio fuso do
                    sistema (aí vale a hora local). Nunca troca em silêncio para o fuso do sistema.
- trava(caminho)    trava exclusiva entre processos (fcntl, msvcrt ou arquivo O_EXCL), a mesma de quadros.py.
"""
import contextlib
import datetime as dt
import glob
import json
import os
import re
import sys
import time

try:
    import fcntl
except ImportError:  # Windows
    fcntl = None
try:
    import msvcrt
except ImportError:  # macOS/Linux
    msvcrt = None

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

class ErroFuso(SystemExit):
    """O fuso pedido não carrega. É um SystemExit com código 3: script que não trata sai com 3 (a linha do erro já
    foi para o stderr). Quem quiser tratar pega ErroFuso (`except Exception` não pega, de propósito)."""

    def __init__(self, nome, motivo):
        self.nome, self.motivo = nome, motivo
        self.mensagem = (f"erro: o fuso {nome} não carregou ({motivo}); instale o tzdata (`python -m pip install tzdata`) "
                         f"ou omita --fuso para usar o fuso do sistema / error: time zone {nome} could not be loaded; "
                         f"install tzdata (`python -m pip install tzdata`) or omit --fuso to use the system time zone")
        super().__init__(3)

    def __str__(self):
        return self.mensagem


def nome_fuso_sistema():
    """Nome IANA do fuso do sistema, quando dá para saber (o mesmo palpite de sistema.py); senão None."""
    try:
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        import sistema  # noqa: E402  (importa caminhos de volta: ok, este módulo já está carregado)
        return sistema.fuso()[0]
    except Exception:
        tz = (os.environ.get("TZ") or "").lstrip(":").strip()
        return tz or None


def fuso(nome=None):
    """tzinfo do fuso IANA `nome`. Vazio → None (= hora local do sistema). Nome que não carrega → ErroFuso,
    salvo quando é o próprio fuso do sistema (aí None, a hora local já é ele)."""
    if not nome:
        return None
    if nome.upper() in ("UTC", "ETC/UTC", "Z"):
        return dt.timezone.utc
    try:
        from zoneinfo import ZoneInfo  # Python 3.9+
    except ImportError:
        ZoneInfo, motivo = None, "Python sem zoneinfo / no zoneinfo"
    if ZoneInfo is not None:
        try:
            return ZoneInfo(nome)
        except Exception as e:  # ZoneInfoNotFoundError, ValueError (nome inválido)
            motivo = f"{type(e).__name__}"
    sis = nome_fuso_sistema()
    if sis and sis.lower() == nome.lower():
        return None  # é o fuso do sistema: a hora local do sistema dá o mesmo resultado
    erro = ErroFuso(nome, motivo)
    print(erro.mensagem, file=sys.stderr)
    raise erro


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


# --- trava entre processos (mesma lógica de quadros.trava) --------------------------------------------------------

ESPERA_TRAVA = 15  # segundos esperando a trava antes de desistir
VELHA_TRAVA = 60   # trava em arquivo (O_EXCL) mais velha que isso = sobra de processo morto


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
            fim = time.time() + ESPERA_TRAVA
            while True:
                try:
                    msvcrt.locking(f.fileno(), msvcrt.LK_NBLCK, 1)
                    break
                except OSError:
                    if time.time() > fim:
                        raise SystemExit(f"trava ocupada há {ESPERA_TRAVA}s: {caminho}")
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
    fim = time.time() + ESPERA_TRAVA
    while True:
        try:
            fd = os.open(excl, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            os.write(fd, str(os.getpid()).encode())
            os.close(fd)
            break
        except FileExistsError:
            try:
                if time.time() - os.path.getmtime(excl) > VELHA_TRAVA:
                    os.remove(excl)  # sobra de um processo que morreu segurando a trava
                    continue
            except OSError:
                continue
            if time.time() > fim:
                raise SystemExit(f"trava ocupada há {ESPERA_TRAVA}s: {excl}")
            time.sleep(0.05)
    try:
        yield
    finally:
        try:
            os.remove(excl)
        except OSError:
            pass


def tudo():
    return {"dados": dados(), "legado": legado(), "pastas_projects": pastas_projects(), "so": so(),
            "pastas_app": pastas_app()}


if __name__ == "__main__":
    if "--tudo" in sys.argv[1:]:
        print(json.dumps(tudo(), ensure_ascii=False, indent=1))
    else:
        print(dados())

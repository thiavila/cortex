#!/usr/bin/env python3
"""O que o Cortex precisa saber da máquina, em JSON (usado ao criar o quadro e no passo de capacidades).

Uso: sh <skills>/tarefas/py <skills>/tarefas/sistema.py

Campos: so, python {versao, executavel}, fuso (IANA ou null), fuso_windows (nome do Windows, só lá), utc_offset,
locale (BCP-47 com `-`, ou null), entrypoint ($CLAUDE_CODE_ENTRYPOINT), app_desktop (há pasta do app com conversas),
git (há `git` no PATH), home, dados (a pasta `<dados>` do SCHEMA).
Nada aqui é decisão: são palpites para sugerir `config/preferencias.fuso/locale` na criação do quadro.
"""
import json
import locale as _locale
import os
import platform
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import caminhos  # noqa: E402

IANA = re.compile(r"^(?:UTC|Etc/[A-Za-z0-9+\-]+|[A-Za-z]+(?:/[A-Za-z0-9_+\-]+)+)$")

# Os nomes de fuso mais comuns do Windows (tzutil /g) → IANA. O resto fica só em `fuso_windows`.
WINDOWS_IANA = {
    "UTC": "Etc/UTC",
    "GMT Standard Time": "Europe/London",
    "W. Europe Standard Time": "Europe/Berlin",
    "Romance Standard Time": "Europe/Paris",
    "Central Europe Standard Time": "Europe/Budapest",
    "Central European Standard Time": "Europe/Warsaw",
    "GTB Standard Time": "Europe/Bucharest",
    "Russian Standard Time": "Europe/Moscow",
    "E. South America Standard Time": "America/Sao_Paulo",
    "Argentina Standard Time": "America/Buenos_Aires",
    "SA Pacific Standard Time": "America/Bogota",
    "Central Standard Time (Mexico)": "America/Mexico_City",
    "Eastern Standard Time": "America/New_York",
    "Central Standard Time": "America/Chicago",
    "Mountain Standard Time": "America/Denver",
    "US Mountain Standard Time": "America/Phoenix",
    "Pacific Standard Time": "America/Los_Angeles",
    "India Standard Time": "Asia/Kolkata",
    "China Standard Time": "Asia/Shanghai",
    "Singapore Standard Time": "Asia/Singapore",
    "Tokyo Standard Time": "Asia/Tokyo",
    "Korea Standard Time": "Asia/Seoul",
    "AUS Eastern Standard Time": "Australia/Sydney",
}


def _ler(p):
    try:
        with open(p, encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _cmd(args):
    try:
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        return r.stdout.strip() if r.returncode == 0 else ""
    except Exception:
        return ""


def fuso():
    """(iana, nome_windows)."""
    tz = (os.environ.get("TZ") or "").lstrip(":").strip()
    if tz and IANA.match(tz):
        return tz, None
    if caminhos.so() == "windows":
        w = _cmd(["tzutil", "/g"])
        return WINDOWS_IANA.get(w), (w or None)
    try:
        alvo = os.path.realpath("/etc/localtime")
        if "zoneinfo/" in alvo:
            n = alvo.split("zoneinfo/", 1)[1]
            if IANA.match(n):
                return n, None
    except Exception:
        pass
    n = _ler("/etc/timezone")
    if n and IANA.match(n):
        return n, None
    return None, None


def _bcp47(v):
    v = (v or "").split(".")[0].split("@")[0].strip()
    if not v or v.upper() in ("C", "POSIX"):
        return None
    v = v.replace("_", "-")
    return v if re.match(r"^[A-Za-z]{2,3}(?:-[A-Za-z0-9]{2,8})*$", v) else None


def locale():
    if caminhos.so() == "windows":
        try:
            import ctypes
            buf = ctypes.create_unicode_buffer(85)
            if ctypes.windll.kernel32.GetUserDefaultLocaleName(buf, 85):
                v = _bcp47(buf.value)
                if v:
                    return v
        except Exception:
            pass
    for v in (os.environ.get("LC_ALL"), os.environ.get("LC_TIME"), os.environ.get("LANG")):
        b = _bcp47(v)
        if b:
            return b
    try:
        b = _bcp47(_locale.getlocale()[0])
        if b:
            return b
    except Exception:
        pass
    if caminhos.so() == "darwin":  # app de GUI costuma não ter LANG
        b = _bcp47(_cmd(["defaults", "read", "-g", "AppleLocale"]))
        if b:
            return b
    try:
        import warnings
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            b = _bcp47(_locale.getdefaultlocale()[0])  # descontinuado no 3.11+, mas ainda útil no Windows
        if b:
            return b
    except Exception:
        pass
    return None


def main():
    iana, win = fuso()
    off = caminhos.agora().strftime("%z")
    out = {
        "so": caminhos.so(),
        "python": {"versao": platform.python_version(), "executavel": sys.executable},
        "fuso": iana,
        "utc_offset": f"{off[:3]}:{off[3:]}" if off else None,
        "locale": locale(),
        "entrypoint": os.environ.get("CLAUDE_CODE_ENTRYPOINT") or None,
        "app_desktop": bool(caminhos.pastas_app()),
        "git": bool(shutil.which("git")),
        "home": os.path.expanduser("~"),
        "dados": caminhos.dados(),
    }
    if caminhos.so() == "windows":
        out["fuso_windows"] = win
    print(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""Explicit, per-profile backend selection. Does not install or start a service."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

from caminhos import trava


class SetupError(Exception):
    pass


def root_path(value=None):
    if value or os.environ.get("CORTEX_LOCAL_DIR"):
        return Path(value or os.environ["CORTEX_LOCAL_DIR"]).expanduser().resolve()
    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / "Cortex"
    if sys.platform == "win32":
        return Path(os.environ.get("LOCALAPPDATA", str(Path.home() / "AppData" / "Local"))) / "Cortex"
    return Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share"))) / "cortex"


def profile_path(root, profile):
    if not profile or not re.fullmatch(r"[a-z0-9][a-z0-9_-]{0,63}", profile):
        raise SetupError("profile_required: choose --profile (lowercase letters, numbers, - or _)")
    return root / "profiles" / (profile + ".json")


def agents_list(values):
    result = []
    for value in values:
        for item in value.split(","):
            item = " ".join(item.strip().lower().split())
            if item in ("claude code", "claude desktop", "claude.ai"):
                item = "claude"
            if not item or len(item) > 64 or any(ord(c) < 32 for c in item):
                raise SetupError("invalid_agents: supply at least one agent name")
            if item not in result:
                result.append(item)
    if not result or len(result) > 20:
        raise SetupError("invalid_agents: supply between 1 and 20 agent names")
    return result


def read_selection(path):
    if not path.exists():
        return None
    if path.stat().st_size > 16384:
        raise SetupError("invalid_selection: profile file is too large")
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
        if (not isinstance(value, dict) or value.get("version") != 1
                or value.get("backend") not in ("artifact", "local")):
            raise ValueError()
        if value["backend"] == "local" and not re.fullmatch(
                r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", value.get("board", "")):
            raise ValueError()
        return value
    except (ValueError, TypeError):
        raise SetupError("invalid_selection: repair the profile explicitly; no fallback was selected")


def atomic_write(path, value):
    fd, tmp = tempfile.mkstemp(prefix=".setup-", dir=str(path.parent))
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def configure(root, profile, agents, name=None, locale=None, fuso=None, replace=False):
    path = profile_path(root, profile)
    agents = agents_list(agents)
    backend = "artifact" if agents == ["claude"] else "local"
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    with trava(str(path) + ".lock"):
        current = read_selection(path)
        if current and current["backend"] != backend and not replace:
            raise SetupError("selection_conflict: changing backend needs --replace-selection after explicit confirmation; data is not migrated")
        value = dict(current) if current and current["backend"] == backend else {
            "version": 1, "profile": profile, "backend": backend}
        value["agents"] = agents
        if backend == "local" and not value.get("board"):
            if not all(isinstance(x, str) and x.strip() for x in (name, locale, fuso)):
                raise SetupError("board_settings_required: supply --name, --locale and --fuso")
            command = [sys.executable, str(Path(__file__).with_name("local.py")), "--root", str(root),
                       "init", "--name", name, "--locale", locale, "--fuso", fuso]
            proc = subprocess.run(command, capture_output=True, text=True, timeout=30)
            if proc.returncode:
                raise SetupError("local_init_failed: local runtime refused initialization; selection was not changed")
            try:
                created = json.loads(proc.stdout)
                board = created["board"]
                if not isinstance(board, str) or not re.fullmatch(
                        r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", board):
                    raise ValueError()
            except (KeyError, ValueError, TypeError):
                raise SetupError("local_init_failed: invalid runtime response; selection was not changed")
            value.update(board=board, name=name)
        atomic_write(path, value)
        return value


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root")
    parser.add_argument("--profile", default=os.environ.get("CORTEX_PROFILE"))
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("status", help="Read selection without creating files")
    commands.add_parser("mcp-config", help="Print MCP config with real paths and board; never installs it")
    setup = commands.add_parser("configure")
    setup.add_argument("--agents", nargs="+")
    setup.add_argument("--name")
    setup.add_argument("--locale")
    setup.add_argument("--fuso")
    setup.add_argument("--replace-selection", action="store_true")
    args = parser.parse_args(argv)
    root = root_path(args.root)
    try:
        path = profile_path(root, args.profile)
        if args.command == "configure":
            agents = args.agents
            if agents is None:
                if not sys.stdin.isatty():
                    raise SetupError("agents_required: ask the user which agents they use, then pass --agents")
                print("Which agents do you use? / Quais agentes você usa? (comma-separated / separados por vírgula)", file=sys.stderr)
                agents = [input()]
            value = configure(root, args.profile, agents, args.name, args.locale, args.fuso, args.replace_selection)
        else:
            value = read_selection(path)
            if args.command == "mcp-config":
                if not value or value["backend"] != "local":
                    raise SetupError("local_setup_required: configure a local board first")
                value = {"mcpServers": {"cortex": {"command": sys.executable, "args": [
                    str(Path(__file__).with_name("local.py").resolve()), "--root", str(root),
                    "--board", value["board"], "mcp"]}}}
            elif value is None:
                value = {"configured": False, "profile": args.profile}
        print(json.dumps(value, ensure_ascii=False))
        return 0
    except (SetupError, OSError, subprocess.TimeoutExpired) as exc:
        message = str(exc) if isinstance(exc, SetupError) else "setup_failed: no selection change confirmed"
        print(json.dumps({"error": message}), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Explicit standalone hook installer. Never changes memories, boards or hook trust."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shlex
import shutil
import stat
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'skills' / 'tarefas'))
from caminhos import trava
from codex_harness import runtime_files


def read(path):
    if path.is_symlink():
        raise ValueError('Refusing symlink: ' + str(path))
    value = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    if not isinstance(value, dict):
        raise ValueError('Expected JSON object: ' + str(path))
    return value


def write(path, value):
    fd, tmp = tempfile.mkstemp(prefix='.cortex-', dir=str(path.parent))
    try:
        if path.exists():
            os.fchmod(fd, stat.S_IMODE(path.stat().st_mode))
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(value, f, ensure_ascii=False, indent=2)
            f.write('\n')
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, path)
    finally:
        if os.path.exists(tmp):
            os.unlink(tmp)


def install(home, remove=False, observe=False):
    if os.name == 'nt':
        raise ValueError('Standalone installer requires POSIX; use WSL on Windows.')
    home = Path(home).expanduser().resolve()
    home.mkdir(parents=True, exist_ok=True)
    managed = home / 'cortex-hooks'
    if managed.is_symlink():
        raise ValueError('Refusing symlink: ' + str(managed))
    managed.mkdir(exist_ok=True, mode=0o700)
    with trava(str(managed / 'install.lock')):
        config_path, receipt_path = home / 'hooks.json', managed / 'install.json'
        original_bytes = config_path.read_bytes() if config_path.exists() else None
        config, receipt = read(config_path), read(receipt_path)
        events = config.setdefault('hooks', {})
        previous = receipt.get('groups', {})
        pending = receipt.get('pending', {})
        recoverable = receipt.get('recoverable', {})
        if not all(isinstance(v, dict) for v in (events, previous, pending, recoverable)):
            raise ValueError('Invalid hooks configuration or receipt')
        owned = {}
        for event in ('UserPromptSubmit', 'SessionStart'):
            groups = events.get(event, [])
            if not isinstance(groups, list):
                raise ValueError(event + ' must be an array')
            owned[event] = [version[event] for version in (previous, pending) if event in version]
            old_versions = recoverable.get(event, [])
            if not isinstance(old_versions, list):
                raise ValueError('Invalid recovery receipt')
            owned[event].extend(old_versions)
            for group in groups:
                handlers = group.get('hooks', []) if isinstance(group, dict) else []
                if (isinstance(handlers, list) and any(isinstance(h, dict) and
                    h.get('statusMessage') == 'Cortex: task board reminder' for h in handlers)
                    and group not in owned[event]):
                    raise ValueError('Cortex hook was edited or installed separately: ' + event)
        if remove and not previous and not pending and not recoverable:
            return {'changed': False, 'installed': False}
        new_groups, runtime = {}, None
        if not remove:
            files = runtime_files(ROOT)
            digest = hashlib.sha256()
            for p in files:
                digest.update(str(p.relative_to(ROOT)).encode())
                digest.update(p.read_bytes())
            runtime = managed / 'runtime' / digest.hexdigest()
            if runtime.exists():
                for p in files:
                    target = runtime / p.relative_to(ROOT)
                    if target.is_symlink() or not target.is_file() or target.read_bytes() != p.read_bytes():
                        raise ValueError('Installed snapshot differs: ' + str(target))
            else:
                runtime.parent.mkdir(exist_ok=True)
                stage = Path(tempfile.mkdtemp(prefix='.stage-', dir=str(runtime.parent)))
                try:
                    for p in files:
                        target = stage / p.relative_to(ROOT)
                        target.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copyfile(p, target)
                    os.rename(stage, runtime)
                finally:
                    if stage.exists():
                        shutil.rmtree(stage)
            command = 'sh ' + shlex.quote(str(runtime / 'skills/tarefas/py')) + ' ' + shlex.quote(str(runtime / 'hooks/codex-tarefas.py'))
            if observe:
                command += ' --observe-dir ' + shlex.quote(str(managed / 'observations'))
            handler = {'type': 'command', 'command': command, 'timeout': 5,
                       'statusMessage': 'Cortex: task board reminder'}
            new_groups = {'UserPromptSubmit': {'hooks': [handler]},
                          'SessionStart': {'matcher': 'startup|resume|compact', 'hooks': [handler]}}
        for event in ('UserPromptSubmit', 'SessionStart'):
            groups = events.get(event, [])
            groups = [g for g in groups if g not in owned[event]]
            if event in new_groups:
                groups.append(new_groups[event])
            if groups or event in events:
                events[event] = groups
        changed = read(config_path) != config
        backup = None
        if changed and config_path.exists():
            backups = managed / 'backups'
            backups.mkdir(exist_ok=True)
            fd, name = tempfile.mkstemp(prefix='hooks-', suffix='.json', dir=str(backups))
            os.close(fd)
            backup = Path(name)
            shutil.copyfile(config_path, backup)
        # Retain both definitions if killed between the two file replacements.
        if (config_path.read_bytes() if config_path.exists() else None) != original_bytes:
            raise ValueError('hooks.json changed during installation; retry without overwriting that edit')
        write(receipt_path, {'version': 1, 'groups': previous, 'pending': new_groups,
                            'recoverable': owned,
                            'runtime': str(runtime) if runtime else None})
        if changed:
            write(config_path, config)
        write(receipt_path, {'version': 2, 'groups': new_groups, 'runtime': str(runtime) if runtime else None, 'observe': bool(observe and not remove)})
        return {'changed': changed, 'installed': not remove, 'ready': False,
                'status': 'removed' if remove else 'verification_required', 'hooks_file': str(config_path),
                'runtime': str(runtime) if runtime else None, 'backup': str(backup) if backup else None,
                'verify_command': 'python3 ' + shlex.quote(str(ROOT / 'skills/tarefas/codex_harness.py')) + ' doctor --codex-home ' + shlex.quote(str(home)) + ' --cwd /absolute/session/folder --session-id EXISTING_SESSION_ID' if runtime else None,
                'trust': 'Review these hooks in Codex Settings > Hooks or /hooks; installer does not grant trust.'}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--codex-home', default=os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    ap.add_argument('--observe', action='store_true', help='Opt in to bounded local execution metadata (no prompt/task content)')
    ap.add_argument('--verify', action='store_true', help='Run read-only native/board verification after installing; incomplete returns exit 2')
    ap.add_argument('--cwd', help='Absolute session folder, required with --verify')
    ap.add_argument('--root', help='Explicit Cortex board root for verification')
    ap.add_argument('--profile', help='Explicit board profile for verification')
    ap.add_argument('--session-id', help='Existing Codex session to verify; never creates a task')
    ap.add_argument('--remove', action='store_true', help='Remove only the exact recorded Cortex hook groups')
    args = ap.parse_args()
    if args.verify and (not args.cwd or not Path(args.cwd).is_absolute() or args.remove):
        ap.error('--verify requires absolute --cwd and cannot be combined with --remove')
    try:
        result = install(args.codex_home, args.remove, args.observe)
        if args.verify:
            from codex_harness import doctor
            result['verification'] = doctor(args.cwd, args.codex_home, ROOT, args.root, args.profile, args.session_id)
            result['ready'] = result['verification']['ready']
            result['status'] = result['verification']['status']
        print(json.dumps(result, ensure_ascii=False))
        return 0 if not args.verify or result['ready'] else 2
    except (ValueError, OSError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())

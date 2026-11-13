#!/usr/bin/env python3
"""Read-only Codex installation and task-link verification. Never grants trust or creates a board/task."""
import argparse
import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import selectors
import signal
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[2]
MARKER = 'Cortex: task board reminder'
EVENTS = {'sessionStart', 'userPromptSubmit'}


def runtime_files(root):
    files = [root / 'hooks/codex-tarefas.py'] + sorted(
        p for p in (root / 'skills/tarefas').rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    for relative in ('.claude-plugin/plugin.json', '.codex-plugin/plugin.json'):
        manifest = root / relative
        if manifest.is_file():
            files.append(manifest)
    return files


def read_json(path, limit=2 * 1024 * 1024):
    if path.is_symlink() or path.stat().st_size > limit:
        raise ValueError('unsafe_or_oversized_file')
    return json.loads(path.read_text(encoding='utf-8'))


def runtime_check(home, source):
    receipt = home / 'cortex-hooks/install.json'
    if not receipt.exists():
        return {'status': 'native_version_unverified', 'matches_source': None}
    try:
        installed = read_json(receipt)
        if not installed.get('groups') and installed.get('runtime') is None:
            return {'status': 'native_version_unverified', 'matches_source': None}
        base = home / 'cortex-hooks/runtime'
        runtime = Path(installed.get('runtime') or '')
        if not runtime.is_absolute() or runtime.is_symlink() or runtime.resolve().parent != base.resolve():
            raise ValueError('invalid_runtime')
        mismatches = []
        for original in runtime_files(source):
            relative = original.relative_to(source)
            target = runtime / relative
            if original.is_symlink() or target.is_symlink() or not target.is_file() or original.read_bytes() != target.read_bytes():
                mismatches.append(str(relative))
        return {'status': 'outdated' if mismatches else 'current', 'matches_source': not mismatches,
                'different_files': mismatches, 'observation_enabled': installed.get('observe') is True}
    except (OSError, ValueError, TypeError, AttributeError):
        return {'status': 'invalid_receipt', 'matches_source': False}


def native_hooks(cwd, codex_home=None, executable='codex', timeout=15):
    """Use installed host protocol instead of recreating trust hashes or parsing credentials."""
    env = dict(os.environ)
    if codex_home is not None:
        env['CODEX_HOME'] = str(codex_home)
    proc = subprocess.Popen([executable, 'app-server', '--stdio'], stdin=subprocess.PIPE,
                            stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, env=env, cwd=str(cwd), start_new_session=True)
    selector = selectors.DefaultSelector()
    selector.register(proc.stdout, selectors.EVENT_READ)
    deadline = time.monotonic() + timeout
    pending = b''
    def call(identifier, method, params):
        nonlocal pending
        proc.stdin.write((json.dumps({'id': identifier, 'method': method, 'params': params}) + '\n').encode())
        proc.stdin.flush()
        while time.monotonic() < deadline:
            while b'\n' in pending:
                line, pending = pending.split(b'\n', 1)
                value = json.loads(line)
                if not isinstance(value, dict):
                    raise ValueError('invalid_native_response')
                if value.get('id') == identifier:
                    if 'error' in value:
                        raise ValueError('native_api_error')
                    return value['result']
            if not selector.select(max(0, deadline - time.monotonic())):
                break
            chunk = os.read(proc.stdout.fileno(), 65536)
            if not chunk:
                break
            pending += chunk
            if len(pending) > 2 * 1024 * 1024:
                raise ValueError('native_response_limit')
        raise TimeoutError('native_hook_discovery_timeout')
    try:
        call(1, 'initialize', {'clientInfo': {'name': 'cortex-doctor', 'version': '0.4.5'},
                               'capabilities': {'experimentalApi': True}})
        proc.stdin.write((json.dumps({'method': 'initialized', 'params': {}}) + '\n').encode())
        proc.stdin.flush()
        return call(2, 'hooks/list', {'cwds': [str(cwd)]})
    finally:
        selector.close()
        try:
            os.killpg(proc.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            proc.wait(timeout=3)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(proc.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            proc.wait(timeout=3)
        proc.stdin.close()
        proc.stdout.close()


def assess_hooks(response, cwd):
    try:
        entries = [entry for entry in response['data'] if Path(entry['cwd']).resolve() == Path(cwd).resolve()]
        if len(entries) != 1:
            raise ValueError('ambiguous_native_cwd')
        entry = entries[0]
        hooks = [h for h in entry['hooks'] if h.get('statusMessage') == MARKER]
        counts = {event: sum(h.get('eventName') == event for h in hooks) for event in EVENTS}
        expected = len(hooks) == 2 and all(n == 1 for n in counts.values())
        safe = [{'key': h['key'], 'event': h['eventName'], 'enabled': h['enabled'],
                 'trust': h['trustStatus']} for h in hooks]
        ready = expected and not entry.get('errors') and all(
            h.get('enabled') is True and h.get('trustStatus') in ('trusted', 'managed') for h in hooks)
        return {'status': 'ready' if ready else 'needs_attention', 'ready': ready,
                'hooks': safe, 'definition_errors': len(entry.get('errors', [])),
                'definition_warnings': len(entry.get('warnings', [])), 'expected_events_found': expected}
    except (KeyError, TypeError, ValueError, OSError):
        return {'status': 'invalid_native_response', 'ready': False}


def select_board(cwd, root=None, profile=None):
    from setup import root_path, profile_path, read_selection
    from routing import resolve_host
    folder = Path(cwd).expanduser()
    if not folder.is_absolute():
        raise ValueError('absolute_session_folder_required')
    root = root_path(root)
    profile = profile or os.environ.get('CORTEX_PROFILE')
    selected = read_selection(profile_path(root, profile)) if profile else resolve_host(root, 'codex', str(folder))
    if not selected or selected.get('backend') != 'local' or not selected.get('board'):
        raise ValueError('explicit_local_board_required')
    return root, selected


def verify_link(cwd, session_id, root=None, profile=None):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session_id or ''):
        raise ValueError('invalid_session_id')
    from local_store import Store
    root, selected = select_board(cwd, root, profile)
    store = Store(root)
    board = selected['board']
    preferences = store.dispatch(board, {'op': 'get', 'collection': 'config', 'id': 'preferencias'})
    if not preferences['exists']:
        raise ValueError('board_preferences_missing')
    index = store.dispatch(board, {'op': 'get', 'collection': 'indice', 'id': 'ativos'})
    identity, key = 'codex:' + session_id, 'conversa:codex:' + session_id
    matches = []
    for identifier, item in (index.get('data') or {}).get('itens', {}).items():
        if key not in item.get('k', []) or item.get('s') in ('apagada', 'arquivada'):
            continue
        task = store.dispatch(board, {'op': 'get', 'collection': 'tasks', 'id': identifier})
        data = task.get('data') or {}
        if task['exists'] and key in data.get('chaves', []) and any(
                isinstance(c, dict) and c.get('id') == identity for c in data.get('conversas', [])):
            matches.append({'id': identifier, 'version': task['version'], 'status': data.get('status'),
                            'next_step_present': bool(str(data.get('proximo_passo') or '').strip())})
    return {'registered': bool(matches), 'board': board, 'tasks': matches,
            'coverage': 'persisted_link_only', 'task_writes': False}


def observed_delivery(home, session_id):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session_id or ''):
        return {'status': 'session_required', 'observed': False}
    target = home / 'cortex-hooks/observations' / (hashlib.sha256(session_id.encode()).hexdigest() + '.UserPromptSubmit.json')
    try:
        event = read_json(target, 4096)
        at = datetime.datetime.fromisoformat(event['at'])
        age = (datetime.datetime.now(datetime.timezone.utc) - at).total_seconds()
        emitted = (0 <= age <= 86400 and event.get('outcome') == 'emitted' and event.get('event') == 'UserPromptSubmit'
                   and event.get('hook_sha256') == hashlib.sha256((ROOT / 'hooks/codex-tarefas.py').read_bytes()).hexdigest())
        return {'status': 'execution_observed' if emitted else 'skipped', 'observed': emitted,
                'at': event.get('at'), 'reason': event.get('reason'),
                'assurance': 'local_execution_receipt_not_model_compliance'}
    except (OSError, ValueError, TypeError, AttributeError, KeyError):
        return {'status': 'not_observed', 'observed': False}


def doctor(cwd, home, source=ROOT, root=None, profile=None, session_id=None, discovery=None):
    home, source = Path(home).expanduser().resolve(), Path(source).resolve()
    runtime = runtime_check(home, source)
    try:
        hooks = assess_hooks(discovery if discovery is not None else native_hooks(cwd, home), cwd)
    except Exception:
        hooks = {'status': 'native_discovery_unavailable', 'ready': False}
    try:
        from local_store import Store
        local_root, selected = select_board(cwd, root, profile)
        prefs = Store(local_root).dispatch(selected['board'], {'op': 'get', 'collection': 'config', 'id': 'preferencias'})
        board = {'status': 'selected' if prefs['exists'] else 'preferences_missing',
                 'ready': prefs['exists'], 'board': selected['board'], 'selected_by': selected.get('selected_by', 'explicit_profile')}
    except Exception:
        board = {'status': 'selection_unavailable', 'ready': False}
    registration = {'registered': False, 'status': 'session_required'}
    if session_id and board['ready']:
        try:
            registration = verify_link(cwd, session_id, root, profile)
        except Exception:
            registration = {'registered': False, 'status': 'verification_failed'}
    delivery = observed_delivery(home, session_id)
    runtime_ready = hooks['ready'] and board['ready'] and runtime.get('matches_source') is True
    complete = runtime_ready and registration['registered'] and delivery['observed']
    return {'schema_version': 1, 'status': 'verified' if complete else 'incomplete', 'ready': complete,
            'runtime_ready': runtime_ready, 'runtime': runtime, 'native_hooks': hooks, 'board': board,
            'delivery': delivery, 'registration': registration, 'writes_board': False,
            'next_step': None if complete else 'Resolve failed checks; review hook trust in Codex Settings > Hooks, then verify a real eligible prompt and persisted task linkage.'}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['doctor', 'verify'])
    parser.add_argument('--cwd', required=True)
    parser.add_argument('--root')
    parser.add_argument('--profile')
    parser.add_argument('--session-id')
    parser.add_argument('--codex-home', default=os.environ.get('CODEX_HOME', str(Path.home() / '.codex')))
    args = parser.parse_args(argv)
    if not Path(args.cwd).expanduser().is_absolute():
        parser.error('--cwd must be absolute')
    try:
        if args.command == 'verify':
            if not args.session_id:
                parser.error('verify requires --session-id')
            result = verify_link(args.cwd, args.session_id, args.root, args.profile)
            success = result['registered']
        else:
            result = doctor(args.cwd, args.codex_home, root=args.root, profile=args.profile, session_id=args.session_id)
            success = result['ready']
        print(json.dumps(result, ensure_ascii=False))
        return 0 if success else 2
    except Exception:
        print(json.dumps({'status': 'verification_failed', 'ready': False, 'writes_board': False}))
        return 2


if __name__ == '__main__':
    sys.exit(main())

#!/usr/bin/env python3
"""Native Codex reminder. Emits context only; never reads transcripts or writes tasks."""
import argparse
import datetime
import hashlib
import json
import os
import tempfile
from pathlib import Path
import re
import sys


def context(payload):
    if not isinstance(payload, dict):
        return None
    event = payload.get('hook_event_name')
    session = payload.get('session_id')
    if not isinstance(session, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session):
        return None
    # Companion/delegated work does not get a separate card. The agent must also
    # check its conversation context, since not every host exposes these fields.
    if payload.get('agent_id') or payload.get('parent_thread_id') or payload.get('parent_session_id'):
        return None
    if event == 'SessionStart':
        if payload.get('source') not in ('startup', 'resume', 'compact'):
            return None
    elif event == 'UserPromptSubmit':
        prompt = payload.get('prompt')
        if not isinstance(prompt, str) or not prompt.strip():
            return None
        if re.match(r'^\s*/(?:[\w-]+:)?(?:bom-dia|boa-noite|tarefas(?:-io)?|quadro-tarefas|clear|compact)\b', prompt, re.I):
            return None
        if prompt.lstrip().startswith(('<task-notification', '<scheduled-task', '<system-reminder')):
            return None
    else:
        return None
    root = Path(__file__).resolve().parent.parent
    skill = root / 'skills' / 'tarefas' / 'SKILL.md'
    local = root / 'skills' / 'tarefas' / 'LOCAL.md'
    return (
        '[Cortex task-board reminder — Codex] Follow the user\'s current scope and permissions first. '
        'For eligible main-thread work, use the current installed tarefas skill and its LOCAL.md. '
        'If that skill is not available, the bundled fallback is ' + str(skill) +
        ' with local-runtime instructions at ' + str(local) + '. '
        'Read the selected board preferences before any mutation. Honor an explicitly selected '
        'profile/board first; otherwise run setup.py resolve --host codex --cwd <session folder> '
        'as described in LOCAL.md. Folder routing requires active Codex rules in the board configuration; '
        'never infer a board from a company name, another host\'s identity, or a connector. '
        'If scope is ambiguous, ask; do not create a database or fall back to an artifact. '
        'Before substantive work, check whether this conversation is linked and search for an analogous '
        'card before creating one. Use conversation identity codex:' + session +
        ' and key conversa:codex:' + session + '; preserve existing links and histories. '
        'During the work and before the final answer, persist meaningful decisions, deliveries, PR/merge/deploy '
        'milestones, blockers and the next step in that card, only when new relevant information exists. '
        'Follow the skill title policy and selected board preferences using the host title tool; existing chats require explicit user authorization to rename. '
        'Respect card_por_conversa (including ask mode and exclusions); never mark done without authorization. '
        'Skip trivial questions, scheduled routines, delegated/subagent/Companion reviews, and board-only routines. '
        'A read-only request or a request not to record anything forbids board writes and takes precedence. '
        'Never message other chats or edit memories/global instructions on the strength of this reminder. '
        'Use the user/board language; give the skill\'s one-line notice only when a card was actually linked '
        'or created. Before claiming a task was saved, run ' + str(root / 'skills/tarefas/codex_harness.py') +
        ' verify with --cwd <absolute session folder> --session-id ' + session +
        ' and the explicitly selected profile/root when applicable; require its persisted-link read-back. '
        'Read-only or excluded work must not create a card merely to satisfy a check. '
        'Installation health is checked separately by codex_harness.py doctor, which must report incomplete '
        'until native trust, actual execution and persisted linkage are verified. '
        'This hook is only a reminder, not evidence that registration succeeded.'
    )


def observe(directory, payload, text):
    """Opt-in, bounded local execution metadata. No prompt, transcript, title or board data."""
    directory = Path(directory).expanduser()
    if directory.is_symlink():
        raise ValueError('unsafe_observation_directory')
    directory.mkdir(parents=True, exist_ok=True, mode=0o700)
    session = payload.get('session_id') if isinstance(payload, dict) else None
    event = payload.get('hook_event_name') if isinstance(payload, dict) else None
    if not isinstance(session, str) or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', session):
        session = None
    if event not in ('SessionStart', 'UserPromptSubmit'):
        event = 'unknown'
    digest = hashlib.sha256(session.encode()).hexdigest() if session else 'invalid'
    record = {'schema_version': 1, 'event': event,
              'at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'outcome': 'emitted' if text else 'skipped',
              'reason': None if text else 'ineligible_or_invalid_payload',
              'hook_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    target = directory / (digest + '.' + event + '.json')
    if target.is_symlink():
        raise ValueError('unsafe_observation_file')
    fd, temporary = tempfile.mkstemp(prefix='.event-', dir=str(directory))
    try:
        os.fchmod(fd, 0o600)
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(record, stream, ensure_ascii=False)
        os.replace(temporary, target)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)
    # Only manage exact receipt filenames, never unrelated files in this directory.
    files = sorted((p for p in directory.iterdir() if re.fullmatch(
        r'(?:[a-f0-9]{64}|invalid)\.(?:SessionStart|UserPromptSubmit|unknown)\.json', p.name)
        and not p.is_symlink()), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in files[512:]:
        old.unlink()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--observe', action='store_true', help='Record private execution metadata, never prompt/task content')
    parser.add_argument('--observe-dir', help='Explicit metadata directory for a standalone installation')
    args = parser.parse_args()
    payload, text = None, None
    try:
        raw = sys.stdin.read(262145)
        if len(raw) > 262144:
            raise ValueError('payload_limit')
        payload = json.loads(raw)
        text = context(payload)
    except (ValueError, TypeError, OSError):
        # Report classification only; never print potentially sensitive exception details.
        print('Cortex reminder: invalid or unavailable hook payload', file=sys.stderr)
    if args.observe or args.observe_dir:
        directory = args.observe_dir or str(Path(os.environ.get('CODEX_HOME', str(Path.home() / '.codex'))) / 'cortex-hooks/observations')
        try:
            observe(directory, payload, text)
        except (ValueError, TypeError, OSError):
            print('Cortex reminder: execution metadata unavailable', file=sys.stderr)
    if text:
        print(json.dumps({'hookSpecificOutput': {
            'hookEventName': payload['hook_event_name'], 'additionalContext': text
        }}, ensure_ascii=False))


if __name__ == '__main__':
    main()

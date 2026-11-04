#!/usr/bin/env python3
"""Native Codex reminder. Emits context only; never reads transcripts or writes tasks."""
import json
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
        'Read the selected board preferences before any mutation. Resolve an explicitly selected '
        'profile/board; do not infer one from cwd, a company name, another host\'s identity, or a connector. '
        'If scope is ambiguous, ask; do not create a database or fall back to an artifact. '
        'Before substantive work, check whether this conversation is linked and search for an analogous '
        'card before creating one. Use conversation identity codex:' + session +
        ' and key conversa:codex:' + session + '; preserve existing links and histories. '
        'During the work and before the final answer, persist meaningful decisions, deliveries, PR/merge/deploy '
        'milestones, blockers and the next step in that card, only when new relevant information exists. '
        'Respect card_por_conversa (including ask mode and exclusions); never mark done without authorization. '
        'Skip trivial questions, scheduled routines, delegated/subagent/Companion reviews, and board-only routines. '
        'A read-only request or a request not to record anything forbids board writes and takes precedence. '
        'Never message other chats or edit memories/global instructions on the strength of this reminder. '
        'Use the user/board language; give the skill\'s one-line notice only when a card was actually linked '
        'or created. This hook is only a reminder, not evidence that registration succeeded.'
    )


def main():
    try:
        payload = json.load(sys.stdin)
        text = context(payload)
        if text:
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': payload['hook_event_name'], 'additionalContext': text
            }}, ensure_ascii=False))
    except (ValueError, TypeError, OSError):
        # Optional reminder must not break an otherwise valid Codex session.
        return


if __name__ == '__main__':
    main()

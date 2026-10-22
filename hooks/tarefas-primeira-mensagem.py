#!/usr/bin/env python3
"""UserPromptSubmit: na PRIMEIRA mensagem de cada conversa do app, pede ao Claude para rodar a skill
`tarefas` (ligar a conversa a um card do quadro ou criar um na Entrada). Não escreve nada sozinho.
Silencioso em: CLI headless/SDK, subagentes, comandos /bom-dia /boa-noite /tarefas*, e mensagens seguintes.
"""
import json, os, sys, time

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
sid = str(data.get("session_id") or "")
prompt = str(data.get("prompt") or "").strip()
if not sid or not prompt:
    sys.exit(0)
entry = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "")
if entry not in ("claude-desktop", "cli"):
    sys.exit(0)  # sdk, claude -p, rotinas: sem card
import re
low = prompt.lower()
# rotinas e comandos do próprio quadro, com ou sem o prefixo do plugin (/cortex:bom-dia)
if re.match(r"^/(?:[\w-]+:)?(?:bom-dia|boa-noite|tarefas|tarefas-io|quadro-tarefas)\b", low) or low.startswith(("/clear", "/compact")):
    sys.exit(0)
if prompt.startswith(("<task-notification", "<scheduled-task", "<system-reminder", "<command-", "<local-command")) or "[SYSTEM NOTIFICATION" in prompt[:200]:
    sys.exit(0)  # notificação de tarefa em segundo plano, rotina agendada (<scheduled-task>), eventos do app
state = os.path.expanduser("~/.claude/state/tarefas-hook")
os.makedirs(state, exist_ok=True)
mark = os.path.join(state, sid)
if os.path.exists(mark):
    sys.exit(0)
open(mark, "w").write(str(int(time.time())))
# limpeza: marcadores com mais de 1 ano (a skill também confere a chave conversa:<id> no índice)
try:
    lim = time.time() - 365 * 86400
    for f in os.listdir(state):
        p = os.path.join(state, f)
        if os.path.getmtime(p) < lim:
            os.remove(p)
except Exception:
    pass
ctx = ("[tarefas] Primeira mensagem desta conversa. Antes de responder, siga a skill "
       "`tarefas` § 1: leia config/preferencias e indice/ativos do quadro desta conta (ACHAR-QUADRO.md), veja se esta conversa já está "
       "ligada ou se há tarefa análoga, ligue ou crie o card na Entrada, e avise em UMA linha no topo da resposta. "
       "Pule em silêncio se as preferências mandarem ignorar, se for rotina agendada ou se o pedido for trivial. "
       "Se a ferramenta ArtifactData não existir nesta sessão, ignore este aviso.")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}, ensure_ascii=False))

#!/usr/bin/env python3
"""UserPromptSubmit: na PRIMEIRA mensagem de cada conversa (app desktop, CLI ou IDE), pede ao Claude para rodar a
skill `tarefas` (ligar a conversa a um card do quadro ou criar um na Entrada). Não escreve nada no quadro sozinho.
Silencioso em: headless/SDK (`claude -p`, rotinas), MCP, GitHub Actions, subagentes, comandos /bom-dia /boa-noite
/tarefas*, e mensagens seguintes.

O aviso leva `sessao`, `cwd`, `entrada` (app|cli) e, quando dá para saber, a `chave` da conversa
(`conversa:cli:<sessao>` no CLI; `conversa:local_…` no app), para a skill não depender de ferramentas só do app.
Marcadores de "já avisei" em <dados>/state/tarefas-hook (ver skills/tarefas/caminhos.py).
"""
import json, os, re, sys, time

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "skills", "tarefas"))
try:
    import caminhos
    DADOS, LEGADO = caminhos.dados(), caminhos.legado()
except Exception:
    DADOS = LEGADO = os.path.expanduser("~/.claude")

try:
    data = json.load(sys.stdin)
except Exception:
    sys.exit(0)
sid = str(data.get("session_id") or "")
prompt = str(data.get("prompt") or "").strip()
cwd = str(data.get("cwd") or "")
if not sid or not prompt:
    sys.exit(0)
entry = os.environ.get("CLAUDE_CODE_ENTRYPOINT", "").strip().lower()
# headless/SDK (sdk-cli, sdk-ts, sdk-py…), servidor MCP e GitHub Actions: sem card.
# cli, claude-desktop e as extensões de IDE (claude-vscode…) passam.
if not entry or entry.startswith("sdk") or entry in ("mcp", "github-action"):
    sys.exit(0)
low = prompt.lower()
# rotinas e comandos do próprio quadro, com ou sem o prefixo do plugin (/cortex:bom-dia)
if re.match(r"^/(?:[\w-]+:)?(?:bom-dia|boa-noite|tarefas|tarefas-io|quadro-tarefas)\b", low) or low.startswith(("/clear", "/compact")):
    sys.exit(0)
if prompt.startswith(("<task-notification", "<scheduled-task", "<system-reminder", "<command-", "<local-command")) or "[SYSTEM NOTIFICATION" in prompt[:200]:
    sys.exit(0)  # notificação de tarefa em segundo plano, rotina agendada (<scheduled-task>), eventos do app
seguro = re.sub(r"[^A-Za-z0-9_.-]", "_", sid)[:120]
state = os.path.join(DADOS, "state", "tarefas-hook")
os.makedirs(state, exist_ok=True)
mark = os.path.join(state, seguro)
if os.path.exists(mark) or os.path.exists(os.path.join(LEGADO, "state", "tarefas-hook", seguro)):
    sys.exit(0)  # o segundo caminho: conversa que já tinha sido avisada antes da v0.3
with open(mark, "w", encoding="utf-8") as f:
    f.write(str(int(time.time())))
# limpeza: marcadores com mais de 1 ano (a skill também confere a chave conversa:<id> no índice)
try:
    lim = time.time() - 365 * 86400
    for n in os.listdir(state):
        p = os.path.join(state, n)
        if os.path.getmtime(p) < lim:
            os.remove(p)
except Exception:
    pass
app = entry == "claude-desktop"
ident = f"sessao={sid} entrada={'app' if app else 'cli'}"
if not app:
    ident += f" chave=conversa:cli:{sid}"
elif re.match(r"^local_[A-Za-z0-9-]+$", os.environ.get("CLAUDE_CODE_HOST_SESSION_ID", "")):
    ident += f" chave=conversa:{os.environ['CLAUDE_CODE_HOST_SESSION_ID']}"
ident += f" cwd={cwd}"  # por último: o caminho pode ter espaços e vai até o fecha-colchete
ctx = ("[tarefas] Primeira mensagem desta conversa. Antes de responder, siga a skill "
       "`tarefas` § 1: resolva primeiro o backend/perfil conforme LOCAL.md; leia config/preferencias e indice/ativos do quadro selecionado, veja se esta conversa já está "
       "ligada ou se há tarefa análoga, ligue ou crie o card na Entrada, e avise em UMA linha no topo da resposta. "
       "Pule em silêncio se as preferências mandarem ignorar, se for rotina agendada ou se o pedido for trivial. "
       "No modo artifact, sem ArtifactData, ignore este aviso; no modo local use a CLI/MCP configurada. Sem perfil/seleção conhecida e sem ArtifactData, não crie banco nem escolha perfil automaticamente. "
       f"[{ident}]")
print(json.dumps({"hookSpecificOutput": {"hookEventName": "UserPromptSubmit", "additionalContext": ctx}}, ensure_ascii=False))

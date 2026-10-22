# Cortex

Quadro de tarefas num artefato do Claude, um card por conversa, `/bom-dia` e `/boa-noite`, empacotado como plugin do
Claude Code (repo público `thiavila/cortex`).

## Milestone atual: v0.3 — agnóstico
Funcionar para qualquer pessoa, de qualquer empresa, em qualquer idioma e máquina (macOS, Windows, Linux; app desktop e
CLI). Tudo o que é específico de uma pessoa ou empresa mora no banco do quadro (`config/*`), descoberto ou perguntado na
criação. Fonte dos achados e das decisões: `DILIGENCIA-v0.3.md` (vale como a etapa de discussão do GSD).

## Restrições
- Colunas fixas (`entrada`, `a_fazer`, `fazendo`, `esperando`, `feito`); só os nomes na tela seguem o idioma.
- Um quadro por conta do Claude.
- Repo público: nada pessoal ou de empresa em exemplos; busca por dados pessoais antes de cada push.
- Quadros v3 existentes continuam funcionando igual depois da migração v3→v4 (o comportamento atual vira preferência).

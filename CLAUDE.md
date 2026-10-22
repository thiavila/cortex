# Cortex — instruções para quem trabalha neste repo

O Cortex é um plugin público do Claude Code. Ele precisa funcionar para **qualquer pessoa, de qualquer empresa**,
em qualquer idioma e sistema operacional. Toda mudança é julgada por esse critério.

## Agnóstico, sempre
- Nada de pessoa, empresa, time, ferramenta, idioma, fuso ou caminho de máquina fixo no código, nas skills ou na página.
- O que é específico de alguém mora no banco do quadro e é descoberto ou perguntado na criação
  (`skills/quadro-tarefas`): `config/preferencias`, `config/fontes`, `config/gestor`, `config/projetos`, `config/tema`.
  O contrato está em `skills/tarefas/SCHEMA.md`; campo novo entra lá, com migração em `skills/tarefas/MIGRACOES.md`
  quando mudar a versão.
- Um gosto pessoal de quem usa vira preferência no banco, nunca regra no texto da skill.
- Ferramentas são descobertas pelos conectores ligados, não pressupostas. Faltou uma ferramenta → a skill segue sem ela.
- Textos da página e dos scripts passam pelo dicionário de idiomas; datas via `Intl`, no fuso do quadro.
- Exemplos sempre genéricos (`Site`, `App`, `ana@empresa.com`). Nada de dados reais.

## Como mudar
1. Trabalhar numa worktree, num branch próprio; PR para `main`.
2. Antes do push: buscar no diff por nomes, e-mails, IDs, caminhos e empresas reais (o repo é público).
3. Commits com o e-mail noreply do GitHub do autor, nunca um e-mail pessoal.
4. Rodar os testes dos scripts e `claude plugin validate .`.
5. Revisão por outro modelo (outra família) antes do merge; corrigir os achados relevantes.
6. Subir a versão em `.claude-plugin/plugin.json` e atualizar o README quando a mudança for visível para quem usa.

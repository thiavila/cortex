# Fase 7 — implementação v0.4 beta

Data: 2026-10-28. Base: 614c337. Branch: codex/cortex-local-runtime.

## Decisão e entrega

Primeiro uso de quadro-tarefas pergunta agentes e perfil. Somente Claude mantém artifact; qualquer outro agente seleciona local. O instalador disponibiliza skills; não há hook interativo de instalação. Seleção persistida por perfil, sem inferir conta nem migrar dados silenciosamente.

- Plano 01: SQLite compartilhado, CLI, servidor loopback autenticado, MCP stdio, versões otimistas, lotes e recibos; índice derivado e limites.
- Plano 02: mesma página do artifact com transporte local, atualização periódica, conflitos sem sobrescrita automática, import/export com prévia e transação em destino vazio, tema sanitizado e fontes do sistema.
- Plano 03: setup, seis skills, documentação e pacotes Claude/Codex v0.4.0. MCP opcional configurado com caminho/UUID reais após seleção. Hook Claude respeita backend local.

## Validação

Ver 07-VERIFICATION.md. Implementação e testes concluídos; revisão de outra família PENDENTE por autenticação do perfil pessoal Claude. Sem aprovação para produção ou merge. Sem instalação nas contas reais, sem migração de dados reais e sem deploy.

## Próximo passo

Restabelecer autenticação do Claude Pessoal pelo fluxo oficial e repetir revisão somente leitura com claude-peer no diff completo desta branch. Corrigir/reavaliar achados, validar attach real no cliente desejado antes de promover o beta. Não alterar conta Daki como fallback.

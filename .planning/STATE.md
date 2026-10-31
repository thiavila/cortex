# Estado

- Milestone: v0.3 (agnóstico). Branch `v0.3-agnostico`, PR thiavila/cortex#1.
- Fases 1–6: feitas. E2E com pessoa en-US (Asana falso, sem git, sem gravador) passou; instalação limpa num
  `CLAUDE_CONFIG_DIR` isolado passou; `claude plugin validate` passa.
- Revisão cruzada (Codex): 1ª NO-GO (16 achados) → corrigidos → reavaliação 13 ok + 3 parciais → corrigidos → GO.
- Pendências: Windows/Linux em máquina real; CLI sem ferramentas de artefato neste build; a página aberta na virada do
  dia não gera as recorrentes do dia novo até recarregar; `--fuso` em Python 3.8 ou Windows sem `tzdata` sai com 3
  (a skill refaz sem fuso).

## v0.4 — Fase 7 implementada; revisão pendente

Setup: Claude exclusivo → artifact; qualquer outro → local compartilhado. Implementação em codex/cortex-local-runtime, base 614c337. 29 testes Python e 4 Node passaram; QA no navegador com dados sintéticos confirmou leitura/escrita em dois processos. Codex reconhece o pacote; manifest Claude validado. Revisão Claude falhou por autenticação do perfil Pessoal, confirmada fora do sandbox: sem aprovação para produção. Próximo passo: restaurar autenticação e revisar o diff completo; validar attach no cliente escolhido. Detalhes em phases/07-runtime-local/07-SUMMARY.md e 07-VERIFICATION.md.

## Quick tasks

| ID | Entrega | Estado |
|---|---|---|
| 261028-wgo | Migração de dois artifacts e preservação de identidades, fontes e vínculos compartilhados | Implementado e validado; revisão cruzada pendente |

| 261029-o7x | Roteamento opt-in por identidade Claude com política no banco; sessão real sem perfil resolveu destino esperado | 35 testes Python; revisão Claude GO restrita ao ajuste; outros P2 da revisão geral pendentes |

| 261031-mgr | Serviço macOS no login, um processo para dois quadros e atalhos de abertura; ~26MiB em repouso | Teste restart/HTTP passou; launchd ativo; Claude GO restrito ao serviço |

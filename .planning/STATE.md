---
gsd_state_version: "1.0"
milestone: v0.3
milestone_name: (agnóstico)
status: unknown
last_updated: "2026-11-03T20:31:16.566Z"
last_activity: 2026-11-03
last_activity_desc: "Quick task 261103-nu7: Codex reminders installed locally; user hook trust pending."
state_head: 8e6d837e4052deffdc5fcc548de28746432fe402
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
---

# Estado

Last activity: 2026-11-03 - Quick task 261103-nu7: Codex reminders installed locally; user hook trust pending.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 261103-nu7 | Codex reminder hooks installed locally; user hook trust pending | 2026-11-03 | 8e6d837 | pending | [261103-nu7-instalar-lembrete-cortex-no-codex-e-dist](./quick/261103-nu7-instalar-lembrete-cortex-no-codex-e-dist/) |

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

| 261031-mm4 | Abas fixas: portas estáveis e autorização persistente opt-in; Arc confirmado após restart | Testes e revisão Claude GO restrita; PR draft |

| 261031-my1 | Favicons por quadro configurados no banco com logos locais originais | 12 testes locais; HTTP e Arc verificados; Claude GO restrito |

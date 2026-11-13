---
gsd_state_version: "1.0"
milestone: v0.3
milestone_name: (agnóstico)
status: unknown
last_updated: "2026-11-04T01:20:45.943Z"
last_activity: 2026-11-03
last_activity_desc: "Quick task 261103-nu7: Codex reminders installed locally; user hook trust pending."
state_head: 4cb310ccc037837fef0b227196aef29f88dbce0f
progress:
  total_phases: 1
  completed_phases: 0
  total_plans: 3
  completed_plans: 0
---

# Estado

Last activity: 2026-11-03 - Quick task 261103-r7p: roteamento por pasta da sessão, Codex GO, PR #4.

### Quick Tasks Completed

| # | Description | Date | Commit | Status | Directory |
|---|-------------|------|--------|--------|-----------|
| 261103-nu7 | Codex reminder hooks installed locally; user hook trust pending | 2026-11-03 | 8e6d837 | pending | [261103-nu7-instalar-lembrete-cortex-no-codex-e-dist](./quick/261103-nu7-instalar-lembrete-cortex-no-codex-e-dist/) |
| 261103-ush | Cortex: achados resolvidos, Claude GO, CI e atestado local para merge autorizado | 2026-11-04 | 4cb310c | complete | [261103-ush-concluir-revisao-e-gates-do-cortex-reuni](./quick/261103-ush-concluir-revisao-e-gates-do-cortex-reuni/) |
| 261103-r7p | Cortex: roteamento por pasta da sessão antes da conta (Codex GO) | 2026-11-03 | 9fe27b6 | complete | [261103-r7p-roteamento-por-pasta-da-sessao](./quick/261103-r7p-roteamento-por-pasta-da-sessao/) |

- Milestone: v0.3 (agnóstico). Branch `v0.3-agnostico`, PR thiavila/cortex#1.
- Fases 1–6: feitas. E2E com pessoa en-US (Asana falso, sem git, sem gravador) passou; instalação limpa num
  `CLAUDE_CONFIG_DIR` isolado passou; `claude plugin validate` passa.
- Revisão cruzada (Codex): 1ª NO-GO (16 achados) → corrigidos → reavaliação 13 ok + 3 parciais → corrigidos → GO.
- Pendências: Windows/Linux em máquina real; CLI sem ferramentas de artefato neste build; a página aberta na virada do
  dia não gera as recorrentes do dia novo até recarregar; `--fuso` em Python 3.8 ou Windows sem `tzdata` sai com 3
  (a skill refaz sem fuso).

## v0.4.2 — Candidato revisado para merge autorizado

Runtime e hooks reunidos; 50 testes Python +13 Node e contratos aprovados. Claude Opus reavaliou o commit4cb310c e deu GO após correções. CI oficial e atestado local configurados. A publicação deve usar local-ci.sh, seguida de CI oficial verde antes do merge do PR #3. Resultado operacional fica no PR e no card cortex-runtime-local. Confiança nos hooks continua pendente no host; não é aprovação de entrega automática.

## Quick tasks

| ID | Entrega | Estado |
|---|---|---|
| 261028-wgo | Migração de dois artifacts e preservação de identidades, fontes e vínculos compartilhados | Implementado e validado; revisão cruzada pendente |

| 261029-o7x | Roteamento opt-in por identidade Claude com política no banco; sessão real sem perfil resolveu destino esperado | 35 testes Python; revisão Claude GO restrita ao ajuste; outros P2 da revisão geral pendentes |

| 261031-mgr | Serviço macOS no login, um processo para dois quadros e atalhos de abertura; ~26MiB em repouso | Teste restart/HTTP passou; launchd ativo; Claude GO restrito ao serviço |

| 261031-mm4 | Abas fixas: portas estáveis e autorização persistente opt-in; Arc confirmado após restart | Testes e revisão Claude GO restrita; PR draft |

| 261031-my1 | Favicons por quadro configurados no banco com logos locais originais | 12 testes locais; HTTP e Arc verificados; Claude GO restrito |


## 2026-11-13 — Roteamento Codex por pasta

Quick 261113-1dc: resolvedor Codex por regras explícitas de pasta, cwd absoluto obrigatório e isolamento de host. 62 testes Python + 13 JavaScript PASS; Claude Opus 5.5 R2 GO. Versão 0.4.4 preparada para CI/instalação oficial; ver quick/261113-1dc-corrigir-roteamento-codex-por-pasta-com-/SUMMARY.md e registro de instalação.

## Installation verification (0.4.5)

Quick 261113-hff: installation doctor, private bounded execution observations and persisted task-link read-back implemented. 77 Python + 13 JavaScript tests pass, manifests validated; Claude cross-family review approved code/local application after corrections. Native hook trust and real prompt acceptance are separate operational gates; see quick summary. Native plugin source version is deliberately unverified until supported.

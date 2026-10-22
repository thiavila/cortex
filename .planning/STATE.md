# Estado

- Milestone: v0.3 (agnóstico). Branch `v0.3-agnostico`, PR thiavila/cortex#1.
- Fases 1–6: feitas. E2E com pessoa en-US (Asana falso, sem git, sem gravador) passou; instalação limpa num
  `CLAUDE_CONFIG_DIR` isolado passou; `claude plugin validate` passa.
- Revisão cruzada (Codex): 1ª NO-GO (16 achados) → corrigidos → reavaliação 13 ok + 3 parciais → corrigidos → GO.
- Pendências: Windows/Linux em máquina real; CLI sem ferramentas de artefato neste build; a página aberta na virada do
  dia não gera as recorrentes do dia novo até recarregar; `--fuso` em Python 3.8 ou Windows sem `tzdata` sai com 3
  (a skill refaz sem fuso).

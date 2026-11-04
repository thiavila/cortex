# Concluir Cortex e merge autorizado

Pedido: reunir o runtime e os hooks, resolver achados relevantes, validar e fazer merge no PR #3. Execução inline com GSD, reutilizando worktree dedicada; não criar segundo PR que repita o runtime.

1. Corrigir concorrência de edições próprias, IDs locais após exclusão, paginação/recuperação, diagnóstico de import e aliases Claude.
2. Adicionar testes de regressão e CI oficial com atestado local; testes baratos continuam no GitHub.
3. Rodar checks, revisão Claude do conjunto e corrigir/reavaliar achados. Consolidar num push, tirar draft após aprovação, aguardar CI no head atual e mergear sem bypass.
4. Atualizar main local e cards/diário; preservar dados, serviço, confiança pendente dos hooks e worktrees usadas pelo runtime.

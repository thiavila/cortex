---
status: complete
---
# Candidato revisado e gates para merge

Candidato de código `4cb310c`, baseado nos hooks `8e6d837`/`cddb096`, que incluem todo o runtime do PR #3. Achados anteriores resolvidos: edições próprias enfileiradas sem ignorar CAS externo, IDs locais após exclusão, leitura paginada com reinício limitado, recuperação de conexão, diagnóstico de import e aliases Claude. Revisão final também corrigiu esgotamento de recibos, escrita sem versão observada e ocorrência recorrente tombstonada.

Recibos preservam permanentemente ID/digest; payloads recentes limitados a10mil/64MiB. Retry de recibo compactado falha com receipt_expired sem reaplicar. Metadados crescem com histórico; custo de examinar payloads ativos permanece uma melhoria de desempenho não bloqueante.

50 testes Python e13 Node passaram fora do sandbox (portas locais necessárias), manifestos e diff check aprovados. Claude Opus GO sobre código exato; REVIEW.md registra limites e uso. CI oficial Linux e atestado local adicionados. Makefile: make ci / make ci-local. Checks baratos rodam sempre no GitHub.

Fila: um único PR #3 reúne runtime e hooks, mantendo draft até revisão concluída. Publicar por local-ci.sh em cópia limpa do commit final, tirar draft, aguardar checks oficiais no head e base atuais e executar merge autorizado. O resultado dessas ações operacionais fica no PR https://github.com/thiavila/cortex/pull/3 e no card cortex-runtime-local do quadro, evitando afirmar aprovação CI antecipadamente neste commit.

Não alterar confiança nos hooks, memórias, política privada ou dados reais. Confiar nos dois hooks continua ação do usuário no próprio Codex. Não remover worktrees usadas pelo serviço ou marketplace. Após merge, atualizar main e fast-forward da worktree do runtime.

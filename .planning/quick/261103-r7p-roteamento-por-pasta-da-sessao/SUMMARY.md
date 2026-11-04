---
status: complete
review: GO
---
# Roteamento por pasta da sessão

Regras de `config/roteamento` aceitam `pastas` (caminhos absolutos), sozinha ou com `conta`. A pasta mais profunda que contém a sessão vence, comparada pela identidade no sistema de arquivos (symlinks, volumes sem distinção de caixa). O login só é lido quando uma regra com conta ainda pode mudar o vencedor. Regras só de conta seguem como fallback, sem mudança para dados existentes. `resolve --cwd`. Nulos explícitos, `organizacao` sem `conta`, caminhos relativos/NUL → `invalid_routing`; cwd inválido → `invalid_cwd`. Versão 0.4.3.

Validação: `scripts/ci/run.sh` (58 testes Python, 13 Node, pacote, diff check) e `claude plugin validate .` passaram. Os testes de regressão de cada achado falham no commit anterior às correções.

Revisão por outra família: implementação Claude Opus 5.5; revisão GPT-6 Codex somente leitura. Primeira rodada NO-GO (2 P1: login consultado antes da precedência, `null` ampliando regras; 3 P2: caixa no macOS, `organizacao` ignorada sem conta, caminho com NUL). Corrigidos em 9fe27b6; reavaliação GO, sem novos achados.

Política concreta (pastas de cada escopo, regras só de conta desativadas para perguntar fora das pastas) fica nos bancos privados, aplicada depois da atualização do plugin.

---
status: complete
review: GO-scoped
---
# Roteamento opt-in por identidade

Política concreta cadastrada somente nos bancos privados, em config/roteamento. Plugin/skills sem conta ou empresa fixa. Resolvedor genérico com adapter Claude consulta autenticação real herdando ambiente; match único por conta e organização opcional. Outros hosts não herdam a política. Sem regra ativa retorna unconfigured e preserva legado; regra ativa sem match/ambiguidade/erro exige escolha explícita e não usa artifact. Perfil explicitamente definido tem precedência.

Validação: 35 testes Python passaram, inclusive quatro novos cenários de roteamento. Manifest Claude validado com aviso legado de CLAUDE.md. Uma sessão real nova do Claude, sem informar perfil nem quadro e sem CORTEX_PROFILE, carregou a skill e retornou o destino esperado via authenticated_host_identity; teste somente leitura, sem manipular tarefas. Configurações privadas ficaram fora do repo.

Revisão Claude somente leitura: primeira NO-GO para ausência de opt-in indistinguível de falta de correspondência; corrigido junto de erros estruturados, validação e precedência; reavaliação GO para este ajuste. Família/modelo: Claude Opus 5.5, implementação OpenAI. Uso agregado de duas revisões + teste de sessão: entrada 26, saída 9316, cache criado 61218/lido 139037; equivalente estimado US$0.7039754.

Versão proposta 0.4.1. Cópias globais locais encaminhadas genericamente para o runtime instalado; regras reais não ficam nessas skills. Outros P2 conhecidos da revisão geral (UI/importação) permanecem pendentes e o PR continua draft, sem merge ou publicação.

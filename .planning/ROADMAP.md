# Roadmap — v0.3 (agnóstico)

| # | Fase | Entrega | Status |
|---|---|---|---|
| 1 | Portabilidade | conversas por SO + reserva por transcritos, lock portátil, lançador de Python, passo de capacidades, resolvedor de caminhos, hook com `session_id`/`cwd` | ✅ |
| 2 | Contrato | SCHEMA v4 (preferências novas, `config/fontes` v2, gestor genérico, campos não documentados), `MIGRACOES.md`, migração v3→v4 | ✅ |
| 3 | Idioma | dicionário pt-BR/en na página e nos scripts, datas via `Intl`, fuso, quadro achado sem depender do título, slugs Unicode | ✅ |
| 4 | Despersonalizar | Granola/gcal/Haiku via config; git/PR atrás de `codigo.usa_git`; automações atrás de `automacao`; modo `perguntar`; sem datas, caminhos e exemplos do autor | ✅ |
| 5 | Criação | descoberta primeiro (conectores, sistema, git), uma ou duas perguntas de confirmação, semear `config/fontes`, `config/projetos` e os campos novos | ✅ |
| 6 | Verificar | `claude plugin validate`; instalação limpa como pessoa fictícia en-US sem Granola, sem git, gestor tipo Asana; scripts nos caminhos de Windows/Linux; revisão do Codex | ✅ |

Fases 1–5 mexem em arquivos que se cruzam pelo contrato (`SCHEMA.md`); a ordem de execução é: contrato primeiro, depois
página e scripts em paralelo com as skills, e a verificação no fim.

## v0.4 — Runtime local (beta, revisão pendente)

| # | Fase | Entrega | Status |
|---|---|---|---|
| 7 | Runtime local | Setup escolhe artifact para Claude exclusivo ou quadro SQLite/HTTP/MCP local para qualquer outro agente; interface compartilhada, migração explícita e pacote Codex | Implementado; revisão cruzada pendente |

Planos: [07-01](phases/07-runtime-local/07-01-PLAN.md), [07-02](phases/07-runtime-local/07-02-PLAN.md), [07-03](phases/07-runtime-local/07-03-PLAN.md).

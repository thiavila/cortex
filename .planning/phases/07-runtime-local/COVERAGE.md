# Cobertura da fase 7

No external API integration: esta fase implementa persistência e protocolos locais do Cortex, preserva o backend Artifact existente e adapta instruções para capacidades já fornecidas pelos hosts. Não adiciona serviço remoto, credenciais ou SDK externo.

| Fonte | ID | Item | Plano | Estado |
|---|---|---|---|---|
| GOAL | LOCAL-01 | Mesmo quadro durável para qualquer agente além do Claude | 07-01, 07-02, 07-03 | COVERED |
| REQ | LOCAL-01 | SQLite, CLI, HTTP e MCP sobre um dispatcher | 07-01 | COVERED |
| REQ | LOCAL-02 | Página interativa com paridade das funções atuais | 07-02 | COVERED |
| REQ | LOCAL-03 | Escolha explícita e roteamento das seis skills | 07-03 | COVERED |
| REQ | LOCAL-04 | Pacote instalável, regressão Claude e migração segura | 07-03 | COVERED |
| RESEARCH | — | Descoberta nesta sessão: schema4, API doc/collection, export existente | 07-01, 07-02 | COVERED |
| CONTEXT | D-01 | Só Claude preserva artifact e propriedade da conta | 07-03 | COVERED |
| CONTEXT | D-02 | Qualquer agente não-Claude usa local | 07-03 | COVERED |
| CONTEXT | D-03 | Dados e comportamento compartilhados | 07-01, 07-02, 07-03 | COVERED |
| CONTEXT | D-04 | Escolha persistida sem autodetecção destrutiva | 07-03 | COVERED |
| CONTEXT | D-05 | Sem hospedagem nem Pages | 07-01, 07-03 | COVERED |
| CONTEXT | D-06 | Migração explícita e preservação | 07-03 | COVERED |

Não havia REQUIREMENTS.md nem RESEARCH.md separado para esta fase; os IDs acima são os requisitos derivados do escopo autorizado, registrados no ROADMAP. Descoberta de código e contratos está no CONTEXT.

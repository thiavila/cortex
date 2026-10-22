# Gestor: Jira

Receita para `config/gestor.tipo = "jira"`. Regras gerais: `<skills>/tarefas/SCHEMA.md` § `config/gestor` e
§ Quadro × gestor. Conector: Atlassian (Rovo) MCP.

## `config`
`{ "cloud_id": "<uuid ou URL do site>", "projeto": "<KEY>", "tipo_issue": "Task", "jql_abertas": "...", "jql_hoje": "..." }`
**Obrigatório:** `cloud_id` e `mapa_status`; para criar, também `projeto` e `tipo_issue`. Faltando `cloud_id` ou o
mapa → `pendente` (sem sincronizar nem escrever); faltando só `projeto`/`tipo_issue` → lê e edita, mas não cria.
- `cloud_id`: de `getAccessibleAtlassianResources`. Mais de um site → o que traz issues da pessoa; na dúvida, perguntar
  uma vez e gravar aqui.
- `projeto` e `tipo_issue`: onde as issues novas são criadas (`getVisibleJiraProjects`,
  `getJiraProjectIssueTypesMetadata`).
- `jql_abertas` (padrão): `assignee = currentUser() AND statusCategory != Done ORDER BY updated DESC`.
- `jql_hoje` (padrão): `assignee = currentUser() AND updated >= startOfDay()`.

## Ler
| Para quê | Chamada |
|---|---|
| Abertas atribuídas a mim (`/bom-dia`) | `searchJiraIssuesUsingJql` `cloudId`, `jql: jql_abertas`, `maxResults: 100`, `fields: [summary, status, project, updated, duedate, parent]`; seguir `nextPageToken` até acabar |
| Mudadas hoje (`/boa-noite`) | idem com `jql_hoje` |
| Uma issue | `getJiraIssue` com `fields` enxutos |
| Buscar por texto (antes de criar) | JQL `project = <projeto> AND (text ~ "<palavras>" OR text ~ "<chave antiga de legado>")`, **sem filtro de status** (todos, inclusive Done). Separar: mesma issue aberta (ligar) · mesma issue fechada (ligar e fechar o card) · nenhuma (trabalho novo) |

Sempre `fields` enxutos: o padrão do conector traz descrição e muito ruído. Chave do card: `jira:PROJ-123`. Link:
`https://<site>/browse/PROJ-123`.

## Escrever (só pelo que a proposta aprovada ou o pedido disser)
| Ação | Chamada |
|---|---|
| Criar | `createJiraIssue` `cloudId`, `projectKey: projeto`, `issueTypeName: tipo_issue`, `summary`, `description`, `assignee_account_id` (de `atlassianUserInfo`), labels das `regras` em `additional_fields` |
| Mudar status | `getTransitionsForJiraIssue` → escolher a transição cujo destino é o nome do `mapa_status` → `transitionJiraIssue` `transition: {id}`. **Nunca adivinhar o id da transição**; sem transição para o destino, dizer e não forçar |
| Comentar | `addCommentToJiraIssue` |
| Campos (título, descrição, labels) | `editJiraIssue` |

## Status
O Jira tem categorias `To Do`, `In Progress`, `Done`; os nomes dos status mudam por projeto. `mapa_status` guarda os
nomes. Ferramenta → coluna, no que o mapa não cobrir: `To Do` → `a_fazer`; `In Progress` → `fazendo`; `Done` →
feito (`descartada` se a resolução for "Won't Do"/"Cancelado" ou o status for o do `mapa_status.descartada`).

## Cuidados
- Comentário de fechamento curto, no idioma da pessoa, sem citar o Claude: "Concluído em DD/MM: <o que foi entregue>".
- Faxina: "Fechado na limpeza de backlog de DD/MM" + transição para `mapa_status.descartada`.

# Gestor: Linear

Receita para `config/gestor.tipo = "linear"`. Regras gerais (o que sincroniza, upsert, `escrever`, `regras`,
`legado`): `<skills>/tarefas/SCHEMA.md` § `config/gestor` e § Quadro × gestor. Conector: o MCP do Linear (as tools
abaixo; o prefixo do nome muda de instalação para instalação).

## `config`
`{ "time": "<key ou nome do time>", "labels_padrao": [], "labels_tipo": [], "usar_cycle": true }`
**Obrigatório:** `time` e `mapa_status`. Faltando → `pendente` (sem sincronizar nem escrever).
- `time`: time onde os itens novos são criados (`list_teams` para descobrir; `get_user "me"` mostra os times da pessoa).
- `labels_padrao`: labels que todo item criado leva. `labels_tipo`: as labels de tipo aceitas (ex.: bug, melhoria),
  para escolher uma ao criar. Conferir os nomes com `list_issue_labels`.
- `usar_cycle`: item criado ou puxado para `fazendo` entra no cycle atual do time (`list_cycles` `type: "current"`).

## Ler
| Para quê | Chamada |
|---|---|
| Abertos atribuídos a mim (`/bom-dia`) | `list_issues` `assignee: "me"`, `limit: 250`, `fields: [id, title, url, status, statusType, project, labels, dueDate, updatedAt, parentId, cycleId]`; seguir `cursor` até acabar. Descartar `statusType` `completed`, `canceled`, `duplicate` |
| Mudados hoje (`/boa-noite`) | `list_issues` `assignee: "me"`, `updatedAt: "-P1D"` (ou o início da janela), mesmos `fields` |
| Um item | `get_issue` `id: "ABC-123"` (com `fields` enxutos; `stateHistory` só se precisar de quando mudou) |
| Buscar por texto (antes de criar) | `list_issues` `query: "<palavras do título>"` (e a chave antiga de `legado`, se o card tiver), `team: <time>`, sem filtro de `state`, `includeArchived: true`: **todos os status** e qualquer responsável. Separar: mesmo item aberto (ligar) · mesmo item fechado (ligar e fechar o card) · nenhum (trabalho novo) |
| Status do time | `list_issue_statuses` `team: <time>` (nome + tipo de cada um) |

Chave do card: `<prefixo_chave>:<identifier>` (ex.: `linear:ABC-123`). Link: o `url` do item.

## Escrever (só pelo que a proposta aprovada ou o pedido disser)
| Ação | Chamada |
|---|---|
| Criar | `save_issue` sem `id`: `team`, `title`, `description` (markdown), `assignee: "me"`, `labels` (`labels_padrao` + a de tipo + as das `regras`), `project` se o card tiver um que exista no Linear, `cycle` se `usar_cycle`, `state` pelo `mapa_status`, `dueDate` = `prazo` |
| Mudar status | `save_issue` `id`, `state: "<nome do mapa_status>"` |
| Comentar | `save_comment` `issueId: "ABC-123"`, `body` |
| Labels | `save_issue` `id`, `addLabels` / `removeLabels` (nunca `labels`, que substitui todas) |
| Projeto / cycle | `save_issue` `id`, `project` / `cycle` |
| Descrição | `save_issue` `id`, `patch` (mexer só no trecho), nunca reescrever a descrição inteira de item de outra pessoa |

## Status
Tipos do Linear: `triage`, `backlog`, `unstarted`, `started`, `completed`, `canceled`, `duplicate`. Cada time dá nomes
próprios; o `mapa_status` guarda os nomes. Sugestão ao configurar (conferir com `list_issue_statuses`):

| Quadro | Tipo no Linear |
|---|---|
| `entrada` | `triage` (sem triagem no time: `backlog`) |
| `a_fazer` | `unstarted` (ou `backlog`) |
| `fazendo` | `started` |
| `esperando` | um `started` de espera, se o time tiver (ex.: "Blocked", "In Review"); senão `null` |
| `feito` | `completed` |
| `descartada` | `canceled` |

Ferramenta → coluna (no que o mapa não cobrir): `triage` → `entrada`; `backlog`/`unstarted` → `a_fazer`; `started` →
`fazendo`; `completed` → feito/`concluida`; `canceled`/`duplicate` → feito/`descartada`.

## Cuidados
- Sub-issues do Linear (`parentId`) que estão atribuídas à pessoa também viram card; o card do pai, se existir, é o `pai`.
- Nunca criar projeto, iniciativa, label ou status novo sem a pessoa pedir.

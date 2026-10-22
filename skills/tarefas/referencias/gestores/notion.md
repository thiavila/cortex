# Gestor: Notion

Receita para `config/gestor.tipo = "notion"` (uma base de tarefas no Notion). Regras gerais:
`<skills>/tarefas/SCHEMA.md` § `config/gestor` e § Quadro × gestor. Conector: Notion MCP.

## `config`
`{ "data_source": "<URL da base, como o notion-fetch devolve>", "campo_titulo": "Name", "campo_status": "Status", "campo_responsavel": "Assignee", "campo_prazo": "Due" }`
**Obrigatório:** `data_source`, `campo_titulo`, `campo_status` e `mapa_status`. Faltando → `pendente` (sem sincronizar
nem escrever).
- `data_source`: achar a base com `notion-search` e ler o esquema com `notion-fetch` (os nomes exatos dos campos vêm
  daí; nunca supor).
- Base pessoal sem campo de responsável: `campo_responsavel: null` (todas as linhas são da pessoa).

## Ler
| Para quê | Chamada |
|---|---|
| Abertas atribuídas a mim (`/bom-dia`) | `notion-query-data-sources` `mode: "rows"`, filtro: `campo_status` diferente dos status de `feito`/`descartada` do mapa e `campo_responsavel` `person_contains` `me` (relativo); seguir o cursor |
| Mudadas hoje (`/boa-noite`) | idem com `last_edited_time` `date_is_on_or_after` `today` |
| Uma página | `notion-fetch` com o id |
| Buscar por texto (antes de criar) | filtro só por `campo_titulo` `string_contains` (**todos os status**), ou `notion-search` restrito à base. Separar: mesma página aberta (ligar) · mesma página fechada (ligar e fechar o card) · nenhuma (trabalho novo) |

Chave do card: `notion:<id da página>`. Link: a URL da página.

## Escrever (só pelo que a proposta aprovada ou o pedido disser)
| Ação | Chamada |
|---|---|
| Criar | `notion-create-pages` com a base como pai, `campo_titulo`, `campo_status` (pelo `mapa_status`), `campo_responsavel`, `campo_prazo` |
| Mudar status / campos | `notion-update-page` `command: "update_properties"` com os nomes exatos dos campos |
| Comentar | `notion-create-comment` na página |

## Status
`mapa_status` guarda os nomes das opções do `campo_status`. Ferramenta → coluna, no que o mapa não cobrir: grupo
"To-do" → `a_fazer`, "In progress" → `fazendo`, "Complete" → feito.

## Cuidados
- Só escrever propriedades que existem no esquema lido; nunca criar campo ou opção nova sem a pessoa pedir.
- Datas no formato do conector (`date:<campo>:start`).

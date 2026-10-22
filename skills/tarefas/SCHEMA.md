# Quadro de tarefas — modelo de dados v3

Contrato único entre a página do quadro (modelo `app/board-src.html`, montada pelo `app/build.py`), as skills `tarefas`, `quadro-tarefas`,
`tarefas-io`, `/bom-dia` e `/boa-noite`. Mudou o modelo? Suba `config/schema.versao`, descreva a
migração aqui e atualize a página e as skills juntas.

O banco é o do artefato (capability `db`). O Claude lê e escreve com a tool `ArtifactData`
(`url` = o quadro desta conta, ver `ACHAR-QUADRO.md`). Toda escrita em documento existente leva
`if_version` (a versão lida por último). Escrever mais de 2 documentos → `batch`.

Pacotes de import/export: sempre gerados pela skill `tarefas-io`, em
`~/.claude/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json` (fora da pasta de skills, que é sincronizada).

## Limites que importam
- 256 KiB por documento, 25 mil documentos e ~20 MB por artefato.
- Sem busca por texto: só filtros por campo (`==`, `in`, `array-contains`, …). Por isso existem
  `tags`, `chaves` e o `indice/ativos`.
- Tarefa madura ≈ 2–4 KB → ~5–8 mil tarefas em `tasks/`. Feitas há 60+ dias vão para
  `arquivo/<AAAA-MM>` (~300 B cada), o que leva a capacidade para dezenas de milhares.

## Coleções

### `tasks/<id>` — uma tarefa
| Campo | Tipo | Notas |
|---|---|---|
| `titulo` | string | curto, verbo no infinitivo quando der |
| `status` | `entrada` \| `a_fazer` \| `fazendo` \| `esperando` \| `feito` | colunas do quadro |
| `resolucao` | `concluida` \| `descartada` \| null | só com `status: feito` |
| `prioridade` | `alta` \| `media` \| `baixa` | |
| `area` | string | id de uma das áreas do escopo (`config/preferencias.areas`) |
| `projetos` | string[] | um ou mais projetos (nome livre), o principal primeiro; cada um espelhado numa tag `projeto:<slug>`; sem repetir o mesmo slug (fica o primeiro nome). Ausente (card de antes da v3) = `[projeto]` + os projetos das outras tags `projeto:` (nome pela regra da migração v2→v3) |
| `projeto` | string | o projeto principal = `projetos[0]` (ou `""`). Fica por compatibilidade: blocos do `/boa-noite`, export e gestor usam o principal |
| `tags` | string[] | `tipo:valor`, minúsculas, sem acento, `-` no lugar de espaço. Tipos: `projeto`, `pessoa`, `tema`, `origem`, `cliente`, `reuniao`, `gestor` (só `gestor:fora`: fica fora do gestor de tarefas). Ex.: `projeto:site`, `pessoa:ana` |
| `chaves` | string[] | identidades externas, para não duplicar: `linear:ABC-123`, `jira:PROJ-42`, `conversa:local_…`, `pr:site#356`, `notion:<id>`, `gcal:<eventId>`, `todoist:<id>`. A do gestor de tarefas usa `config/gestor.prefixo_chave` |
| `pai` | string \| null | id da tarefa-mãe (projeto → subtarefas) |
| `relacionadas` | string[] | ids de tarefas ligadas de outro assunto (a ligação é gravada nos dois lados) |
| `prazo` | `AAAA-MM-DD` \| null | |
| `proximo_passo` | string | a próxima ação concreta |
| `contexto` | string | pessoas, decisões, por que existe |
| `resumo` | string | 1–2 frases do estado atual; o `/boa-noite` mantém |
| `links` | `{rotulo, url}[]` | só `https://` |
| `conversas` | `{id, titulo, link, arquivada, papel?}[]` | `link` = `claude://claude.ai/epitaxy/<id>`; `papel`: `original` (fala com o usuário e orquestra) \| `executor` (aberta por tarefa sugerida; reporta à original) |
| `historico` | `{em, texto, por?}[]` | mais recente primeiro, no máximo 50; `por`: `pagina` \| `tarefas` \| `fechar` \| `bom-dia` \| `boa-noite` \| `io` |
| `fonte` | `{tipo, ref}` | `manual` \| `conversa` \| `recorrente` \| `linear` \| `jira` \| `notion` \| `diario` \| `import` (item do gestor: `{tipo: <config/gestor.tipo>, ref: <ID>}`) |
| `auto` | bool | card criado sozinho (primeira mensagem de uma conversa, ou ocorrência de recorrente) |
| `recorrente` | string \| ausente | id em `recorrentes/` quando o card é uma ocorrência dela |
| `criado_em`, `atualizado_em`, `concluido_em` | ISO 8601 UTC | |

Id: `kebab-case` curto e estável (`site-pr-356`), ou a chave externa quando houver uma só
(`ABC-123`). Nunca reaproveitar id de tarefa apagada.

### `indice/ativos` — o que o Claude lê para achar tarefas
```json
{ "itens": { "<id>": { "t": "titulo", "s": "status", "p": "projeto principal", "ps": ["todos os projetos"], "tags": [], "k": ["chaves"], "pai": null, "u": "atualizado_em" } },
  "atualizado_em": "ISO" }
```
- Toda escrita numa tarefa (página ou skill) também faz `update` em `indice/ativos` com
  `{"itens": {"<id>": {...}}}` (o merge é por chave, então escritas de tarefas diferentes não se atropelam).
- Tarefa apagada: `{"itens": {"<id>": {"s": "apagada"}}}`. Tarefa arquivada: `{"s": "arquivada"}`.
- O `/boa-noite` reescreve o índice inteiro a partir de `tasks/` (tira apagadas/arquivadas, corrige divergências).

### `config/preferencias` — o jeito do usuário
```json
{
  "escopo": "trabalho", "nome": "Trabalho", "sub": "Linear + conversas",
  "areas": [{"id": "produto", "nome": "Produto"}, {"id": "dados", "nome": "Dados"}],
  "idioma": "pt-BR",
  "tags_conhecidas": ["projeto:site", "pessoa:ana"],
  "card_por_conversa": { "ativo": true, "modo": "criar_e_avisar",
                         "ignorar_titulos": ["Bom dia", "Boa noite", "<nome de rotina agendada>"],
                         "ignorar_cwd": [] },
  "titulo_conversa": { "automatico": true, "max": 25 },
  "fechar": { "modo": "perguntar" },  // "perguntar" = o agente sugere e pergunta; "desligado" = só quando o usuário pede
  "parada_dias": 14, "zumbi_dias": 60, "arquivar_feitas_dias": 60,
  "regras_fechamento": ["Conversa que terminou esperando o usuário e ele não voltou = encerrada"],
  "agendas": ["voce@empresa.com"],
  "export": { "destino": null, "mapa_status": {} },
  "notas": ["preferências livres que o usuário foi dizendo, com data"]
}
```
`principal: true` desempata quando a mesma conta tem mais de um quadro. Toda skill lê este documento antes de agir. Quando o usuário corrige um comportamento, a skill
registra a preferência aqui (em `notas` ou no campo certo) e avisa em uma linha.
`export` está **obsoleto desde a v2**: o gestor de tarefas mora em `config/gestor`. Quadro sem `config/gestor` ainda lê
`export.destino`/`export.mapa_status` como reserva; ninguém escreve mais em `export`.

### `config/tema` — o visual da marca (opcional)
Só existe se o quadro foi vestido com a marca da pessoa (`quadro-tarefas` § Tema). Sem ele, o quadro usa o tema neutro.
```json
{ "nome": "Empresa X", "origem": "https://empresa-x.com",
  "css": ":root { --accent: #0A5BD7; ... } @media (prefers-color-scheme: dark) { ... }",
  "fontes": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap",
  "atualizado_em": "ISO" }
```
- `css`: só sobrescrita de tokens e ajustes leves de forma; vai inteiro no `--tema-arquivo` do `build.py` ao remontar.
- `fontes`: URL do Google Fonts ou `null`. Nunca guardar arquivo de fonte, logo ou imagem aqui.
- Quem remonta a página (troca de tema, versão nova do plugin) lê este documento para não perder a marca.

### `config/projetos` — projetos e suas pastas (v3)
Liga cada projeto às pastas do computador e aos repositórios dele. É o que deixa o `/bom-dia` (e a skill `tarefas`)
saber, pela pasta da conversa, de qual projeto ela é.
```json
{ "itens": { "site": { "nome": "Site",
                       "pastas": ["/Users/ana/Github/site"],
                       "repos": ["ana/site"] } },
  "raizes": ["/Users/ana", "/Users/ana/Github"],
  "atualizado_em": "ISO" }
```
- Chave de `itens` = `slug(nome)`, o mesmo da tag `projeto:<slug>`. `nome` = o nome usado em `projetos` dos cards.
- `pastas`: caminhos absolutos; vale a pasta e tudo dentro dela (inclusive `.claude/worktrees/…`).
- `repos`: `dono/nome` do `origin`, para reconhecer worktrees fora da pasta (ex.: `~/.codex/worktrees/…`).
- `raizes`: pastas que agrupam vários projetos (home, `~/Github`, pasta da conta). Ali nada é perguntado: o quadro é inteiro.
  Sem `raizes` (ou sem o documento), as raízes padrão são: home, `~/Github` e as pastas-mãe de
  `config/preferencias.fontes.repos` (`~/Github/Projetos/**` → `~/Github/Projetos`). Com `raizes`, vale só a lista.
- **Achar o projeto de uma pasta** (`cwd`, com `realpath`): (1) a pasta é uma raiz → nenhum; (2) a pasta mais longa de
  `pastas` que contém o `cwd` → esse projeto; (3) `git -C <cwd> remote get-url origin` → `dono/nome` em `repos`;
  (4) nada → pasta sem projeto.
- Sem o documento = sem projetos cadastrados (tudo é pasta sem projeto; raízes = as padrão, acima).
  Quem cria é o `/bom-dia`, quando a pessoa pede "criar projeto pra esta pasta". Projeto que só existe nos cards
  (sem pasta) não precisa estar aqui.

### `config/gestor` — o gestor de tarefas da pessoa (v2)
Um por quadro. Diz qual ferramenta externa de tarefas a pessoa usa e como as skills leem e escrevem nela.
```json
{
  "tipo": "linear",
  "nome": "Linear da empresa",
  "prefixo_chave": "linear",
  "config": { "time": "ABC", "labels_padrao": [], "labels_tipo": [], "usar_cycle": true },
  "mapa_status": { "entrada": "Triage", "a_fazer": "Todo", "fazendo": "In Progress", "esperando": null,
                   "feito": "Done", "descartada": "Canceled" },
  "escrever": { "criar": "propor_no_boa_noite", "editar": "propor_no_boa_noite" },
  "regras": ["toda issue do dia a dia leva a label X", "não criar projetos nem iniciativas"],
  "legado": [{ "tipo": "jira", "prefixo": "jira", "ate": "AAAA-MM-DD", "acao": "ignorar" }],
  "pendente": false,
  "atualizado_em": "ISO"
}
```
| Campo | Notas |
|---|---|
| `tipo` | `linear` \| `jira` \| `notion` \| `nenhum`. Receita de cada um em `<skills>/tarefas/referencias/gestores/<tipo>.md` |
| `nome` | rótulo livre, usado nas propostas ("📤 Linear da empresa") |
| `prefixo_chave` | prefixo das chaves dos cards: `linear` → `linear:ABC-123`. Padrão = `tipo` |
| `config` | específico do tipo. `linear`: `{time, labels_padrao, labels_tipo, usar_cycle}`; `jira`: `{cloud_id, projeto, tipo_issue, jql_abertas, jql_hoje}`; `notion`: `{data_source, campo_titulo, campo_status, campo_responsavel, campo_prazo}`. Só IDs e nomes, nunca token |
| `mapa_status` | coluna do quadro (e `descartada`) → status na ferramenta. `null` = sem equivalente: o quadro muda sozinho, a ferramenta não. O caminho inverso (ferramenta → coluna) usa este mapa e, no que faltar, a receita do tipo |
| `escrever.criar`, `escrever.editar` | `propor_no_boa_noite` (o `/boa-noite` propõe; grava só com o ok) \| `sob_pedido` (só quando a pessoa pede aquela escrita) \| `nunca` |
| `regras` | regras da casa, em texto livre. Toda skill que escreve na ferramenta aplica (label obrigatória, o que nunca criar, padrão de título…) |
| `legado` | ferramentas antigas. `acao: "ignorar"`: chaves com esse `prefixo` não são lidas nem sincronizadas; os cards ficam como estão, até a pessoa tirar |
| `pendente` | `true` = configuração incompleta. Também conta como pendente, com ou sem a marca, o gestor sem o `config` obrigatório do tipo (§ Obrigatório da receita) ou sem `mapa_status`. Pendente → nada é lido, sincronizado nem escrito no gestor até o setup completar e a pessoa confirmar (`/bom-dia` oferece; `/quadro-tarefas gestor` faz); aí `pendente: false` |

Sem `config/gestor` = `tipo: "nenhum"`: nada é lido nem escrito em gestor externo. O `/bom-dia` e o `/quadro-tarefas`
oferecem configurar uma vez (sugestão pelos conectores ligados); "não uso" grava `{tipo: "nenhum"}` e a pergunta não volta.
Se o texto de `config/fontes` também descrever o gestor, vale o `config/gestor` (avisar a diferença em uma linha).

### Quadro × gestor — a regra da relação
**Tudo o que vem do gestor está no quadro, mas nem tudo do quadro vai para o gestor:** um item do gestor pode ser feito
de várias tarefas intermediárias no quadro.
- **Gestor → quadro: sempre.** O `/bom-dia` traz todo item aberto atribuído à pessoa como card: chave
  `<prefixo_chave>:<ID>`, `fonte: {tipo: <tipo>, ref: <ID>}`, `links` com a URL do item. Card com a mesma chave já
  existe → atualiza, não duplica.
- **Quadro → gestor: só o trabalho de nível de cima.** Card com `pai` é etapa: nunca vai sozinho para o gestor. Se o
  `pai` tem chave do gestor, os filhos são as etapas daquele item, e todos os filhos feitos são evidência de que o
  item pode fechar. Se o `pai` não tem chave, quem pode ir é o card de cima.
- **Escrita é sempre upsert, proposta no `/boa-noite`**, gravada só depois do ok. Cada operação respeita o seu modo:
  editar → `escrever.editar`; criar → `escrever.criar`; ligar a item existente é edição do card, e a edição que vier
  junto segue `escrever.editar`.
  - Card com chave do gestor → **editar**: status pela coluna e pela `resolucao` (`feito` + `concluida` →
    `mapa_status.feito`; `feito` + `descartada` → `mapa_status.descartada`; demais colunas → o mapa delas),
    comentário curto no idioma da pessoa sem citar o Claude, título/descrição só se o escopo mudou.
  - **Nunca devolver ao gestor o que veio dele:** item já no status equivalente, ou mudança do card que só espelhou o
    gestor (evidência = o próprio item) → nenhuma escrita.
  - Card de nível de cima sem chave do gestor **e sem chave de `legado`**, que é trabalho de verdade (não pessoal, não
    trivial, não filho) → **criar**, mas antes buscar no gestor em **todos os status**: item aberto que é o mesmo →
    ligar (acrescentar a chave) e editar; item já fechado que é o mesmo → ligar e fechar o card pela resolução dele
    (nunca reabrir nem criar outro); nenhum → trabalho novo, criar. Criou → gravar a chave nova no card.
  - Card cuja única chave externa é de `legado` → nunca criar automaticamente; só **ligar**, se a busca achar no
    gestor um item que claramente é ele (mesmo título ou a chave antiga citada no item). Sem achado claro → fica só
    no quadro.
- **Faxina:** item do gestor parado há `zumbi_dias`+ → proposta de ir para `mapa_status.descartada`.
- **Legado:** chaves de um `legado.prefixo` não são lidas nem escritas.
- **Item novo do gestor sem card com a chave dele:** antes de criar card, procurar análogo entre os cards abertos
  (Regras de escrita 1 e skill `tarefas` § 1.4): chave antiga de `legado` citada no item, mesmo título, ou mesmo
  objetivo no mesmo projeto. Achado claro → **ligar** (acrescentar a chave nesse card); dúvida → perguntar no
  briefing, sem criar; nada → card novo.
- Nunca vai para o gestor: link `claude://`, conteúdo de conversa, dado pessoal ou segredo.

### `config/schema`
`{ "formato": "quadro-tarefas", "versao": 3, "escopo": "trabalho", "criado_em": "ISO", "migracoes": ["v1 em 2026-10-04", "v2 em 2026-10-08", "v3 em 2026-10-20"] }`
`formato` marca o artefato como quadro: é por ele que as skills reconhecem o quadro na lista de artefatos da
conta (`ACHAR-QUADRO.md`). Quadros criados antes de 05/10 não têm; a primeira escrita acrescenta.

#### Migrações
- **v1 → v2 (08/10): `config/gestor`.** Quem acha `versao: 1` na primeira escrita da rodada (`ACHAR-QUADRO.md` § 6),
  num `batch` com `if_version`: se `config/preferencias.export.destino` é `linear`, `jira` ou `notion` (qualquer caixa) e
  ainda não há `config/gestor`,
  semear `config/gestor` com `tipo` = destino (minúsculo), `nome` = destino, `prefixo_chave` = `tipo`, `mapa_status` =
  `export.mapa_status`, `config: {}`, `escrever: {criar: "sob_pedido", editar: "propor_no_boa_noite"}` (o comportamento
  da v1: só fechar issue terminada), `regras: []`, `legado: []`, **`pendente: true`** (falta o `config` obrigatório:
  nada de sincronizar nem escrever até o setup descobrir e a pessoa confirmar); e `config/schema` com `versao: 2` e
  `"v2 em AAAA-MM-DD"` em `migracoes`. Sem `export.destino`: só sobe a versão (falta de `config/gestor` = `nenhum`).
  `export` fica onde está e é lido só como reserva.
- **v2 → v3 (20/10): card em vários projetos + `config/projetos`.** Na primeira escrita da rodada que achar `versao: 2`,
  num `batch` com `if_version`: para cada card com mais de uma tag `projeto:` e sem `projetos`, gravar `projetos` =
  `[projeto, …os outros]` (nome de cada slug = o `projeto` de outro card com esse slug; sem nenhum, o slug com hífen virando espaço e
  cada palavra com maiúscula) e o `ps` no índice; `config/schema` com `versao: 3` e `"v3 em AAAA-MM-DD"`. Os demais cards ficam:
  ausência de `projetos` vale `[projeto]`. `config/projetos` não é semeado (nasce quando a pessoa cadastra uma pasta).


### `dias/<AAAA-MM-DD>` — o diário (substitui `DIARIO-*.md`)
```json
{
  "bom_dia": { "gerado_em": "ISO", "foco": ["<id>"],
               "plano": [{"texto": "...", "tarefa": "<id>|null", "feito": false, "chip": "<task_id do spawn_task>|null"}],
               "reunioes": [{"hora": "10:00", "titulo": "...", "tarefas": ["<id>"], "nota": "..."}],
               "destravar": ["decisões que só o usuário toma"] },
  "boa_noite": { "gerado_em": "ISO", "cobre": ["AAAA-MM-DD"],
                 "plano": [{"texto": "...", "tarefa": "<id>|null", "marca": "x|~| "}],
                 "fechado": ["..."], "pendente": ["..."], "foco_amanha": ["<id>"],
                 "conversas": [{"id": "local_…", "titulo": "...", "resumo": "...", "tarefa": "<id>|null", "acao": "arquivada|mantida"}],
                 "custo": {"modelo": "haiku", "tokens_in": 0, "tokens_out": 0, "usd": 0} },
  "fechados": [{"em": "ISO", "conversa": "local_…", "titulo": "...", "tarefa": "<id>", "resumo": "...", "status": "feito|esperando"}]
}
```
`bom_dia.rodadas` (v3): `[{em, recorte: "<slug do projeto>|todos", agenda: "detalhada|resumida|nenhuma"}]`, uma por rodada
do `/bom-dia` (o recorte por projeto é o do § Recorte por pasta da skill). Item do `plano` escolhido numa rodada com
recorte leva `projeto: <slug>`. Rodadas do mesmo dia **unem** `plano`, `reunioes`, `foco` e `destravar` (nunca
substituem o que outra rodada gravou).
`fechados` é escrito pela skill `fechar` ao longo do dia; `bom_dia.gerado_em` pode ser uma lista quando o `/bom-dia` roda
mais de uma vez (cada rodada acrescenta ao `plano`).

### `recorrentes/<id>` — tarefas que se repetem (decidido em 14/10)
Uma lista de modelos. Quando chega o dia de uma ocorrência, ela vira um card normal em `a_fazer` e anda pelo quadro
como qualquer tarefa. A página tem a aba **Recorrentes** (criar, editar, pausar, apagar) e o botão **↻ no quadro**
que mostra/esconde os cards gerados.
```json
{ "titulo": "Fechar o financeiro", "ativo": true,
  "regra": { "tipo": "diaria|semanal|mensal", "a_cada": 1, "inicio": "AAAA-MM-DD",
             "dias": [1, 3],        // semanal: 1=seg … 7=dom
             "dia": 5 },            // mensal: dia do mês; -1 = último; dia maior que o mês = último
  "antecedencia_dias": 0,           // o card aparece N dias antes da data
  "projeto": "", "area": "", "prioridade": "media", "tags": [], "proximo_passo": "", "contexto": "", "links": [],
  "ultima": "AAAA-MM-DD",           // última ocorrência já tratada (com card ou anotada)
  "criado_em": "ISO", "atualizado_em": "ISO" }
```
- **Gerar** (página ao abrir, e o `/bom-dia` com `<skills>/tarefas/recorrentes.py`; a regra é a mesma nos dois): pega
  a ocorrência mais recente entre `ultima`+1 e hoje+`antecedencia_dias`.
  - Sem card aberto da recorrente → card `<id>--<AAAA-MM-DD>` em `a_fazer`, `prazo` = a data, `recorrente: <id>`,
    tag `recorrente:<id>`, chave `recorrente:<id>@<data>`, `fonte: {tipo: "recorrente", ref: <id>}`, `auto: true`.
  - Card anterior ainda aberto → **não duplica**: só uma linha no `historico` dele ("nova ocorrência chegou").
  - Ocorrências que passaram sem ninguém abrir o quadro não viram card (o histórico diz quantas).
  - Depois, `ultima` = a ocorrência tratada. O id determinístico evita card duplo se página e skill gerarem juntas.
- Pausar/retomar: `ativo`. Retomar não gera o que passou na pausa. Mudar a regra recomeça a contar de hoje.
- Apagar a recorrente não apaga os cards que ela já gerou.
- Os modelos não entram no `indice/ativos`; os cards gerados entram como qualquer tarefa.

### `arquivo/<AAAA-MM>` — feitas compactadas
`{ "itens": { "<id>": { "titulo", "projeto", "tags", "chaves", "resolucao", "concluido_em", "resumo" } } }`
Mês = mês do `concluido_em`. A tarefa sai de `tasks/` só depois de gravada aqui.

## Concorrência (limite conhecido)
O banco não tem transação. As skills escrevem com `if_version` (conflito → reler e refazer). A página escreve sem
versão (last-writer-wins): se a página e uma skill mudarem a MESMA tarefa no mesmo instante, a lista de um lado
(conversas, histórico, tags) pode sobrescrever a do outro. Para um usuário só é raro; o `/boa-noite` reconcilia o
índice a partir de `tasks`. Se o quadro virar compartilhado por várias pessoas, mover `historico` e `conversas`
para subcoleções (`tasks/<id>/historico/<ts>`).

## Regras de escrita (todas as skills)
1. Antes de criar: procurar no `indice/ativos` por chave igual (`k`) e por título/tags parecidos. Achou → atualizar.
2. Toda mudança de status, prazo ou ligação ganha uma linha em `historico` (com `por`).
3. `atualizado_em` muda a cada escrita; `concluido_em` só ao ir para `feito`.
4. Ligação em `relacionadas` é sempre gravada nos dois lados (batch com as duas tarefas + índice).
5. Nada de segredo, token ou dado de cartão em nenhum campo.

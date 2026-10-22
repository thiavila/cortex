# Quadro de tarefas — modelo de dados v4

Contrato único entre a página do quadro (modelo `app/board-src.html`, montada pelo `app/build.py`), as skills `tarefas`, `quadro-tarefas`,
`tarefas-io`, `/bom-dia`, `/boa-noite` e `fechar`. Mudou o modelo? Suba `config/schema.versao`, descreva a
migração em `MIGRACOES.md` e atualize a página e as skills juntas.

O banco é o do artefato (capability `db`). O Claude lê e escreve com a tool `ArtifactData`
(`url` = o quadro desta conta, ver `ACHAR-QUADRO.md`). Toda escrita em documento existente leva
`if_version` (a versão lida por último). Escrever mais de 2 documentos → `batch`.

**Nada da pessoa nem da empresa fica nas skills, nos scripts ou na página:** idioma, fuso, ferramentas, gestor de tarefas,
jeito de trabalhar e regras da casa moram nos documentos `config/*` deste banco.

`<dados>` = a pasta de estado local do Cortex: `$CORTEX_DADOS`, senão `$CLAUDE_CONFIG_DIR`, senão `~/.claude`
(`python3 <skills>/tarefas/caminhos.py` imprime a pasta resolvida). Pacotes de import/export: sempre gerados pela skill
`tarefas-io`, em `<dados>/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json` (fora da pasta de skills).

**Python:** os scripts rodam com `sh <skills>/tarefas/py <script>` (acha `python3`, `python` ou `py -3`; no Windows o
`sh` é o do Git Bash, que o Claude Code usa).

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
| `status` | `entrada` \| `a_fazer` \| `fazendo` \| `esperando` \| `feito` | colunas do quadro. Os ids são fixos; o nome na tela segue o idioma |
| `resolucao` | `concluida` \| `descartada` \| null | só com `status: feito` |
| `prioridade` | `alta` \| `media` \| `baixa` | ids fixos; o nome na tela segue o idioma |
| `area` | string | id de uma das áreas do escopo (`config/preferencias.areas`); sem área → `area_padrao` |
| `projetos` | string[] | um ou mais projetos (nome livre, qualquer escrita), o principal primeiro; cada um espelhado numa tag `projeto:<slug>`; sem repetir o mesmo slug (fica o primeiro nome). Ausente (card de antes da v3) = `[projeto]` + os projetos das outras tags `projeto:` |
| `projeto` | string | o projeto principal = `projetos[0]` (ou `""`). Fica por compatibilidade: blocos do `/boa-noite`, export e gestor usam o principal |
| `tags` | string[] | `tipo:valor`, minúsculas, `-` no lugar de espaço (§ Slugs). Tipos: `projeto`, `pessoa`, `tema`, `origem`, `cliente`, `reuniao`, `recorrente`, `gestor` (só `gestor:fora`: fica fora do gestor de tarefas). Ex.: `projeto:site`, `pessoa:ana` |
| `chaves` | string[] | identidades externas, para não duplicar: `<prefixo_chave do gestor>:<ID>`, `conversa:<id>` (app: `conversa:local_…`; CLI: `conversa:cli:<uuid>`), `pr:<repo>#<n>`, `agenda:<eventId>`, `recorrente:<id>@<data>`. Quadros antigos podem ter `gcal:<eventId>`: vale como `agenda:` |
| `pai` | string \| null | id da tarefa-mãe (projeto → subtarefas) |
| `relacionadas` | string[] | ids de tarefas ligadas de outro assunto (a ligação é gravada nos dois lados) |
| `prazo` | `AAAA-MM-DD` \| null | data no fuso do quadro |
| `proximo_passo` | string | a próxima ação concreta |
| `contexto` | string | pessoas, decisões, por que existe |
| `resumo` | string | 1–2 frases do estado atual; o `/boa-noite` mantém |
| `links` | `{rotulo, url}[]` | só `https://` |
| `conversas` | `{id, titulo, link, retomar?, arquivada, papel?}[]` | app: `id` = `local_…`, `link` = `claude://claude.ai/epitaxy/<id>`. CLI: `id` = `cli:<uuid>`, `link: null`, `retomar: "claude --resume <uuid>"`. `papel`: `original` (fala com o usuário e orquestra) \| `executor` (aberta por tarefa sugerida; reporta à original) |
| `historico` | `{em, texto, por?}[]` | mais recente primeiro, no máximo 50; texto no idioma do quadro; `por`: `pagina` \| `tarefas` \| `fechar` \| `bom-dia` \| `boa-noite` \| `io` |
| `fonte` | `{tipo, ref}` | `manual` \| `conversa` \| `recorrente` \| `diario` \| `import` \| `<config/gestor.tipo>` (item do gestor: `{tipo: <tipo>, ref: <ID>}`) |
| `auto` | bool | card criado sozinho (primeira mensagem de uma conversa, ou ocorrência de recorrente) |
| `recorrente` | string \| ausente | id em `recorrentes/` quando o card é uma ocorrência dela |
| `criado_em`, `atualizado_em`, `concluido_em` | ISO 8601 UTC | |

Id: `kebab-case` curto e estável (`site-pr-356`), ou a chave externa quando houver uma só
(`ABC-123`). Nunca reaproveitar id de tarefa apagada.

### Slugs
Slug de projeto, tag e id = o texto em minúsculas, sem acentos (NFD, marcas combinantes fora), e tudo que não é letra
ou número de qualquer escrita (`\p{L}`, `\p{N}`) nem `:` vira `-`. Latim fica como antes (`Gestão` → `gestao`);
nomes em chinês, árabe, cirílico etc. ficam com as letras deles (`项目` → `项目`). A página (`slug()`) e os scripts
(`slug_projeto()` do `io.py`) seguem a mesma regra.

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
  "escopo": "trabalho", "nome": "Trabalho", "sub": "", "principal": true,
  "areas": [{"id": "geral", "nome": "Geral"}], "area_padrao": "geral",
  "idioma": "en", "locale": "en-US", "fuso": "America/New_York", "semana_inicia": 7,
  "dias_uteis": [1, 2, 3, 4, 5], "horario": {"inicio": "09:00", "fim": "18:00"},
  "tags_conhecidas": ["projeto:site", "pessoa:ana"], "exemplo_projeto": "Site",
  "card_por_conversa": { "ativo": true, "modo": "criar_e_avisar", "ignorar_titulos": [], "ignorar_cwd": [] },
  "titulo_conversa": { "automatico": false, "max": 25, "manter": [] },
  "fechar": { "modo": "perguntar" },
  "automacao": { "encaminhar_plano": "perguntar", "renomear_conversas": false, "arquivar_conversas": "propor",
                 "ancora_memoria": false, "linha_claude_md": false },
  "codigo": { "usa_git": false, "remoto": "origin", "branch_base": null, "ruido": [], "copiar_fora_do_git": false },
  "resumo": { "modelo": null, "confirmar_acima": 15 },
  "parada_dias": 14, "zumbi_dias": 60, "arquivar_feitas_dias": 60,
  "regras_fechamento": [],
  "notas": ["preferências livres que o usuário foi dizendo"]
}
```
| Campo | Notas |
|---|---|
| `escopo`, `nome`, `sub` | rótulo livre do quadro (`escopo` = slug do nome) e o subtítulo da página |
| `principal` | desempata quando a mesma conta tem mais de um quadro (`ACHAR-QUADRO.md`) |
| `areas`, `area_padrao` | áreas que separam assuntos dentro do quadro; uma só esconde o filtro. `area_padrao` = a usada quando nada diz a área (página, recorrentes, skills); sem ela, a primeira de `areas` |
| `idioma` | idioma das respostas, dos textos gravados e da página (`pt-BR`, `en`, …). A página tem textos em `pt-BR` e `en`; outro idioma usa o `en` na página e o próprio idioma nas skills |
| `locale` | BCP-47 do formato de data e número (`en-US`, `pt-BR`, `en-GB`). Ausente = `idioma` |
| `fuso` | IANA (`America/Sao_Paulo`). "Hoje", prazos e janelas do `/boa-noite` são contados nele. Ausente = o fuso do sistema/navegador |
| `semana_inicia` | `1` (segunda) \| `7` (domingo). Ausente = o costume do `locale` |
| `dias_uteis`, `horario` | dias (1=seg … 7=dom) e horário de trabalho: o `/bom-dia` não cobra reunião nem prazo fora deles |
| `tags_conhecidas` | tags preferidas ao inferir tags de um card novo |
| `exemplo_projeto` | nome de projeto mostrado na dica do campo rápido da página (`#Site`) |
| `card_por_conversa` | `ativo`; `modo`: `criar_e_avisar` (cria o card e avisa) \| `perguntar` (só propõe, não grava sem o ok); `ignorar_titulos` (trechos de título ou primeira mensagem), `ignorar_cwd` (pastas). Rotinas agendadas, subagentes e os comandos do próprio Cortex já ficam de fora pelo hook, sem precisar de lista |
| `titulo_conversa` | `automatico`: dar nome curto à conversa nova (só onde há `set_session_title`); `max`: tamanho; `manter`: ids de conversas que nunca são renomeadas nem fechadas por sugestão |
| `fechar.modo` | `perguntar` (o agente sugere fechar a conversa quando a entrega acaba e pergunta) \| `desligado` (só quando o usuário pede) |
| `automacao.encaminhar_plano` | o que o `/bom-dia` faz com os itens escolhidos: `chips` (abre uma tarefa sugerida por item, sem perguntar) \| `perguntar` (oferece abrir, item a item numa pergunta só) \| `nao` (só o plano) |
| `automacao.renomear_conversas` | o `/bom-dia`/`/boa-noite` renomeiam a própria conversa e propõem nomes curtos às outras |
| `automacao.arquivar_conversas` | `propor` (o `/boa-noite` propõe arquivar as que acabaram) \| `nao` |
| `automacao.ancora_memoria` | a skill `tarefas` grava, na memória da pasta, que tarefas vão para o quadro |
| `automacao.linha_claude_md` | a criação do quadro oferece uma linha no `CLAUDE.md` global apontando para o quadro |
| `codigo.usa_git` | `false` → nenhuma evidência de git/PR (commits, `git status`, PR mergeado) é buscada nem cobrada |
| `codigo.remoto`, `codigo.branch_base` | remoto e branch de base para "commit sem push" (`git log <remoto>/<base>..HEAD`). `branch_base: null` = a branch padrão do remoto (`git symbolic-ref refs/remotes/<remoto>/HEAD`) |
| `codigo.ruido` | caminhos que não contam como mudança pendente no `git status` (arquivos gerados por sincronização, por exemplo) |
| `codigo.copiar_fora_do_git` | antes de arquivar uma conversa numa worktree, copiar o arquivo novo fora do git para o checkout principal (`false` = só avisar) |
| `resumo.modelo` | modelo dos subagentes que resumem conversas no `/boa-noite`: `null` = o padrão de subagente da sessão; ou um nome aceito pela ferramenta de subagentes (`haiku`, `sonnet`…) |
| `resumo.confirmar_acima` | acima de quantos subagentes numa rodada o `/boa-noite` pede ok antes |
| `parada_dias`, `zumbi_dias`, `arquivar_feitas_dias` | tarefa parada (aviso), zumbi (faxina) e quando as feitas vão para `arquivo/` |
| `regras_fechamento` | regras extras do `/boa-noite` para fechar sem evidência explícita (ex.: "conversa que terminou esperando o usuário e ele não voltou = encerrada"). Vazio = só fecha com evidência explícita |
| `notas` | preferências livres, uma por linha |

Toda skill lê este documento antes de agir. Quando o usuário corrige um comportamento, a skill registra a preferência
aqui (no campo certo ou em `notas`) e avisa em uma linha. **Campo ausente** num quadro migrado da v3 vale o que a
migração v3→v4 gravou; num quadro novo, o padrão do exemplo acima (o mais contido).

### `config/fontes` — as ferramentas da pessoa (v2)
De onde o `/bom-dia` e o `/boa-noite` coletam, e quem a pessoa é em cada ferramenta. Semeado na criação do quadro pela
descoberta dos conectores ligados (`quadro-tarefas` § 2) e confirmado pela pessoa.
```json
{ "versao": 2,
  "agenda":   { "conector": "<nome do conector de agenda>", "calendarios": ["voce@empresa.com"], "eu": "voce@empresa.com" },
  "reunioes": { "conector": "<gravador ou notas de reunião>", "eu": "Ana" },
  "chat":     [{ "conector": "<chat>", "eu": "@ana", "canais": [] }],
  "email":    { "conector": "<e-mail>", "eu": "voce@empresa.com" },
  "codigo":   { "host": "<github|gitlab|…>", "repos": ["dono/nome"], "eu": "<login>" },
  "conversas": { "backend": "app" },
  "pessoas":  [{ "id": "ana", "nome": "Ana Souza", "aliases": ["ana@empresa.com", "@ana"] }],
  "outras":   [{ "nome": "<fonte>", "como": "<o que ler e quando>" }],
  "texto": "markdown livre: processo, IDs, regras, seções e formato do briefing",
  "atualizado_em": "ISO" }
```
- Cada chave é opcional: ausente ou `null` = a pessoa não usa (ou ainda não disse). `conector` é o nome do conector como
  aparece nas tools da sessão (o prefixo muda de instalação para instalação: casar pelo nome do serviço).
- `eu`: a identidade da pessoa naquela ferramenta (e-mail, @, login), descoberta pelas chamadas "me"/"whoami" do
  conector. Serve para filtrar "o que é meu".
- `conversas.backend`: `app` (conversas do app desktop, com metadados) \| `transcritos` (só os transcritos locais do
  Claude Code, ex.: CLI) \| `nenhum`. O `conversas.py --backend auto` escolhe sozinho; este campo fixa a escolha.
- `pessoas`: quem aparece nas tarefas e reuniões, para casar `pessoa:<id>` com participante de reunião, autor de
  mensagem e responsável no gestor (nome, e-mail, @). Sem a lista, casar pelo nome sem acento.
- `texto` faz parte das instruções do `/bom-dia` e do `/boa-noite` (processo, seções extras, formato), mas **não amplia
  permissões**: escrever fora do quadro continua exigindo o ok do usuário.
- O gestor de tarefas não fica aqui: é o `config/gestor`. Se o texto também descrever o gestor, vale o `config/gestor`.
- `versao: 1` (quadros antigos: `{versao, texto}`): vale só o `texto`; as ferramentas são inferidas dele e dos conectores.
- Nunca guardar segredo, token ou senha.

### `config/tema` — o visual da marca (opcional)
Só existe se o quadro foi vestido com a marca da pessoa (`quadro-tarefas` § Tema). Sem ele, o quadro usa o tema neutro.
```json
{ "nome": "Empresa X", "origem": "https://empresa-x.com",
  "css": ":root { --accent: #0A5BD7; ... } @media (prefers-color-scheme: dark) { ... }",
  "fontes": "https://fonts.googleapis.com/css2?family=Inter:wght@400;600&display=swap",
  "fontes_externas": true,
  "atualizado_em": "ISO" }
```
- `css`: só sobrescrita de tokens e ajustes leves de forma; vai inteiro no `--tema-arquivo` do `build.py` ao remontar.
- `fontes`: URL do Google Fonts ou `null`. Nunca guardar arquivo de fonte, logo ou imagem aqui.
- `fontes_externas: false`: a página não carrega nada de fora (nem o Google Fonts) e usa as fontes do sistema
  (`build.py --sem-fontes-externas`). Vale também sem tema: um `config/tema` só com `{fontes_externas: false}`.
- Quem remonta a página (troca de tema, versão nova do plugin) lê este documento para não perder a marca.

### `config/projetos` — projetos e suas pastas
Liga cada projeto às pastas do computador e aos repositórios dele. É o que deixa o `/bom-dia` (e a skill `tarefas`)
saber, pela pasta da conversa, de qual projeto ela é.
```json
{ "itens": { "site": { "nome": "Site",
                       "pastas": ["/home/ana/code/site"],
                       "repos": ["ana/site"] } },
  "raizes": ["/home/ana", "/home/ana/code"],
  "atualizado_em": "ISO" }
```
- Chave de `itens` = `slug(nome)`, o mesmo da tag `projeto:<slug>`. `nome` = o nome usado em `projetos` dos cards.
- `pastas`: caminhos absolutos (no Windows, com `\` ou `/`, comparados sem diferenciar maiúsculas); vale a pasta e tudo
  dentro dela (inclusive worktrees dentro dela).
- `repos`: `dono/nome` do remoto, para reconhecer worktrees fora da pasta.
- `raizes`: pastas que agrupam vários projetos (home, a pasta de código). Ali nada é perguntado: o quadro é inteiro.
  Sem `raizes` (ou sem o documento), a raiz padrão é só a home. A criação do quadro descobre e confirma as outras
  (§ 2 da `quadro-tarefas`).
- **Achar o projeto de uma pasta** (`cwd`, com `realpath`): (1) a pasta é uma raiz → nenhum; (2) a pasta mais longa de
  `pastas` que contém o `cwd` → esse projeto; (3) com `codigo.usa_git`, `git -C <cwd> remote get-url <remoto>` →
  `dono/nome` em `repos`; (4) nada → pasta sem projeto.
- Sem o documento = sem projetos cadastrados (tudo é pasta sem projeto). Quem cria é a criação do quadro ou o
  `/bom-dia`, quando a pessoa pede "criar projeto pra esta pasta". Projeto que só existe nos cards não precisa estar aqui.

### `config/gestor` — o gestor de tarefas da pessoa
Um por quadro. Diz qual ferramenta externa de tarefas a pessoa usa e como as skills leem e escrevem nela.
```json
{
  "tipo": "linear",
  "nome": "Linear da empresa",
  "prefixo_chave": "linear",
  "config": { "time": "ABC", "labels_padrao": [], "labels_tipo": [], "usar_cycle": true },
  "receita": null,
  "leitura": { "filtro": "atribuido_a_mim", "texto": "" },
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
| `tipo` | `linear` \| `jira` \| `notion` \| `generico` \| `nenhum`. Receita de cada um em `<skills>/tarefas/referencias/gestores/<tipo>.md`. `generico` = qualquer outra ferramenta com conector (Asana, ClickUp, GitHub Issues, Azure DevOps, Trello, Todoist, Monday…): a receita é descoberta pelo conector e guardada em `receita` |
| `nome` | rótulo livre, usado nas propostas ("📤 Asana da empresa") |
| `prefixo_chave` | prefixo das chaves dos cards: `linear` → `linear:ABC-123`. Padrão = `tipo`; no `generico`, o nome curto da ferramenta (`asana`, `clickup`, `gh`) |
| `config` | específico do tipo. `linear`: `{time, labels_padrao, labels_tipo, usar_cycle}`; `jira`: `{cloud_id, projeto, tipo_issue, jql_abertas, jql_hoje}`; `notion`: `{data_source, campo_titulo, campo_status, campo_responsavel, campo_prazo}`; `generico`: o que a receita precisar (workspace, projeto, quadro…). Só IDs e nomes, nunca token |
| `receita` | só no `generico` (`gestores/generico.md`): `{conector, eu, ler_abertas, ler_mudadas, buscar, ler_um, criar, mudar_status, comentar, link, status}`, cada um dizendo a tool do conector e os argumentos. Nos outros tipos, `null` (a receita é o arquivo) |
| `leitura` | o que entra no quadro: `filtro` = `atribuido_a_mim` (padrão) \| `criado_por_mim` \| `seguindo` \| `projeto` \| `consulta`; `texto` = o detalhe (projeto, consulta salva, JQL, filtro do conector) |
| `mapa_status` | coluna do quadro (e `descartada`) → status na ferramenta. `null` = sem equivalente: o quadro muda sozinho, a ferramenta não. O caminho inverso (ferramenta → coluna) usa este mapa (duas colunas com o mesmo status → a mais adiantada delas, fora `feito`) e, no que faltar, a receita do tipo |
| `escrever.criar`, `escrever.editar` | `propor_no_boa_noite` (o `/boa-noite` propõe; grava só com o ok) \| `sob_pedido` (só quando a pessoa pede aquela escrita) \| `nunca` |
| `regras` | regras da casa, em texto livre. Toda skill que escreve na ferramenta aplica (label obrigatória, o que nunca criar, padrão de título…) |
| `legado` | ferramentas antigas. `acao: "ignorar"`: chaves com esse `prefixo` não são lidas nem sincronizadas; os cards ficam como estão, até a pessoa tirar |
| `pendente` | `true` = configuração incompleta. Também conta como pendente, com ou sem a marca, o gestor sem o obrigatório da receita (§ Obrigatório) ou sem `mapa_status`. Pendente → nada é lido, sincronizado nem escrito no gestor até o setup completar e a pessoa confirmar (`/bom-dia` oferece; `/quadro-tarefas gestor` faz); aí `pendente: false` |

Sem `config/gestor` = `tipo: "nenhum"`: nada é lido nem escrito em gestor externo. O `/bom-dia` e o `/quadro-tarefas`
oferecem configurar uma vez (sugestão pelos conectores ligados); "não uso" grava `{tipo: "nenhum"}` e a pergunta não volta.

**Quando o quadro fala com o gestor** sai daqui, não de uma regra fixa: o caminho gestor → quadro é sempre leitura; o
caminho quadro → gestor segue `escrever.criar`/`escrever.editar` (com `propor_no_boa_noite`, o que vai para o gestor é
proposto no `/boa-noite` e só gravado com o ok).

### Quadro × gestor — a regra da relação
**Tudo o que vem do gestor está no quadro, mas nem tudo do quadro vai para o gestor:** um item do gestor pode ser feito
de várias tarefas intermediárias no quadro.
- **Gestor → quadro: sempre.** O `/bom-dia` traz todo item aberto que passa na `leitura` (padrão: atribuído à pessoa)
  como card: chave `<prefixo_chave>:<ID>`, `fonte: {tipo: <tipo>, ref: <ID>}`, `links` com a URL do item. Card com a
  mesma chave já existe → atualiza, não duplica.
- **Quadro → gestor: só o trabalho de nível de cima.** Card com `pai` é etapa: nunca vai sozinho para o gestor. Se o
  `pai` tem chave do gestor, os filhos são as etapas daquele item, e todos os filhos feitos são evidência de que o
  item pode fechar. Se o `pai` não tem chave, quem pode ir é o card de cima.
- **Escrita é sempre upsert**, no modo de cada operação: editar → `escrever.editar`; criar → `escrever.criar`; ligar a
  item existente é edição do card, e a edição que vier junto segue `escrever.editar`.
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
`{ "formato": "quadro-tarefas", "versao": 4, "pagina": "0.3.0", "escopo": "trabalho", "criado_em": "ISO", "migracoes": [] }`
`pagina` = a versão do plugin que montou a página publicada; mais antiga que o plugin → `quadro-tarefas` § Atualizar a
página.
`formato` marca o artefato como quadro: é por ele que as skills reconhecem o quadro na lista de artefatos da
conta (`ACHAR-QUADRO.md`), seja qual for o título. Quadro novo nasce na versão atual, com `migracoes: []`.
`versao` abaixo de 4 → as migrações de `MIGRACOES.md`, em ordem, na primeira escrita da rodada.

### `dias/<AAAA-MM-DD>` — o diário
A data é a do fuso do quadro (`config/preferencias.fuso`).
```json
{
  "bom_dia": { "gerado_em": "ISO", "foco": ["<id>"],
               "plano": [{"texto": "...", "tarefa": "<id>|null", "feito": false, "chip": "<task_id da tarefa sugerida>|null", "conversa": "<id>|null"}],
               "reunioes": [{"hora": "10:00", "titulo": "...", "tarefas": ["<id>"], "nota": "..."}],
               "destravar": ["decisões que só o usuário toma"],
               "rodadas": [{"em": "ISO", "recorte": "<slug do projeto>|todos", "agenda": "detalhada|resumida|nenhuma"}] },
  "boa_noite": { "gerado_em": "ISO", "cobre": ["AAAA-MM-DD"],
                 "plano": [{"texto": "...", "tarefa": "<id>|null", "marca": "x|~| "}],
                 "fechado": ["<título> — <evidência>"], "pendente": ["<id>"], "foco_amanha": ["<id>"],
                 "conversas": [{"id": "local_…|cli:…", "titulo": "...", "resumo": "...", "tarefa": "<id>|null", "acao": "arquivada|mantida|fechada_no_dia"}],
                 "custo": {"modelo": "<modelo dos subagentes>", "subagentes": 0, "tokens_in": 0, "tokens_out": 0, "usd": 0} },
  "fechados": [{"em": "ISO", "conversa": "local_…|cli:…", "titulo": "...", "tarefa": "<id>", "resumo": "...", "status": "feito|esperando"}]
}
```
- `bom_dia.rodadas`: uma por rodada do `/bom-dia` (o recorte por projeto é o do § Recorte por pasta da skill). Item do
  `plano` escolhido numa rodada com recorte leva `projeto: <slug>`. Rodadas do mesmo dia **unem** `plano`, `reunioes`,
  `foco` e `destravar` (nunca substituem o que outra rodada gravou). `bom_dia.gerado_em` pode ser uma lista quando o
  `/bom-dia` roda mais de uma vez.
- `fechados` é escrito pela skill `fechar` ao longo do dia.

### `recorrentes/<id>` — tarefas que se repetem
Uma lista de modelos. Quando chega o dia de uma ocorrência, ela vira um card normal em `a_fazer` e anda pelo quadro
como qualquer tarefa. A página tem a aba **Recorrentes** (criar, editar, pausar, apagar) e o botão **↻** que
mostra/esconde os cards gerados.
```json
{ "titulo": "Revisar as metas da semana", "ativo": true,
  "regra": { "tipo": "diaria|semanal|mensal", "a_cada": 1, "inicio": "AAAA-MM-DD",
             "dias": [1, 3],        // semanal: 1=seg … 7=dom
             "dia": 5 },            // mensal: dia do mês; -1 = último; dia maior que o mês = último
  "antecedencia_dias": 0,           // o card aparece N dias antes da data
  "projeto": "", "area": "", "prioridade": "media", "tags": [], "proximo_passo": "", "contexto": "", "links": [],
  "ultima": "AAAA-MM-DD",           // última ocorrência já tratada (com card ou anotada)
  "criado_em": "ISO", "atualizado_em": "ISO" }
```
- **Gerar** (página ao abrir, e o `/bom-dia` com `<skills>/tarefas/recorrentes.py`; a regra é a mesma nos dois): pega
  a ocorrência mais recente entre `ultima`+1 e hoje+`antecedencia_dias` (hoje no fuso do quadro).
  - Sem card aberto da recorrente → card `<id>--<AAAA-MM-DD>` em `a_fazer`, `prazo` = a data, `recorrente: <id>`,
    tag `recorrente:<id>`, chave `recorrente:<id>@<data>`, `fonte: {tipo: "recorrente", ref: <id>}`, `auto: true`,
    `area` = a da recorrente, senão `area_padrao`.
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
2. Toda mudança de status, prazo ou ligação ganha uma linha em `historico` (com `por`), no idioma do quadro.
3. `atualizado_em` muda a cada escrita; `concluido_em` só ao ir para `feito`.
4. Ligação em `relacionadas` é sempre gravada nos dois lados (batch com as duas tarefas + índice).
5. Nada de segredo, token ou dado de cartão em nenhum campo.

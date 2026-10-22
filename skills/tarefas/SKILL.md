---
name: tarefas
description: >
  Quadro de tarefas do usuário (artefato com banco): o destino de QUALQUER pedido para salvar, anotar,
  acompanhar ou lembrar uma tarefa ou pendência, em qualquer projeto ("salva como task", "salva isso como
  uma task pra eu fazer depois", "anota pra depois", "cria uma tarefa", "preciso lembrar de X", "tenho que
  fazer Y", "anota no quadro", "registra essa tarefa", "cria um card"; English: "save this as a task",
  "add a card", "remind me to", "what's on the board about X"). O pedido vai para o quadro, não direto para o
  gestor de tarefas externo da pessoa: o que vai para o gestor, e quando, segue config/gestor.escrever no
  banco do quadro. Também liga a conversa atual ao card certo e procura tarefas parecidas antes de criar.
  Roda sozinha na primeira mensagem de cada conversa (o hook tarefas-primeira-mensagem pede) e sempre que o
  usuário disser "o que tem no quadro sobre X", "liga isso à tarefa Y", "marca como esperando", "isso é um
  projeto novo", ou quando a conversa tiver um marco claro (PR aberto/mergeado, decisão tomada, bloqueio em
  terceiro). Lê e escreve o banco do artefato com a tool ArtifactData. Contrato de dados em SCHEMA.md.
user_invocable: true
argument-hint: "(nenhum) | registrar <texto> | buscar <texto> | ligar <id> | status <id> <coluna>"
---

# tarefas — o quadro como memória do dia

`<skills>` = a pasta-mãe do Base directory desta skill (vale numa pasta de skills e dentro do plugin).
Scripts: `sh <skills>/tarefas/py <script>` (acha o Python certo em macOS, Windows e Linux).

O quadro é a memória e a visualização do usuário. Esta skill é quem escreve nele durante o dia; o
`/bom-dia` abre o dia e o `/boa-noite` fecha. Modelo de dados: `<skills>/tarefas/SCHEMA.md`
(ler a parte de `tasks`, `indice/ativos` e `config/preferencias` antes da primeira escrita da sessão).

**Idioma:** títulos, próximos passos, histórico e avisos no idioma de `config/preferencias.idioma` (sem ele, o do usuário).
Datas e "hoje" no `fuso` do quadro.

## 0. Qual quadro
O quadro é o da conta do Claude desta sessão: seguir `<skills>/tarefas/ACHAR-QUADRO.md` (o § 0 diz o que fazer quando
falta uma ferramenta do app desktop, como no CLI). Sem quadro nesta conta → não escrever; dizer em uma linha e sugerir
`quadro-tarefas`.

## 0b. Memória da pasta (só com `config/preferencias.automacao.ancora_memoria: true`)
A memória do Claude Code é por pasta de projeto (`<config>/projects/<slug-da-raiz-do-projeto>/memory/`, com `<config>` =
`$CLAUDE_CONFIG_DIR` ou `~/.claude`, índice `MEMORY.md`): uma sessão lê só a memória da raiz do projeto dela. Com a
âncora ligada, na pasta onde a sessão roda:
1. **Garantir a âncora.** Se essa memória não tem uma dizendo que tarefas e pendências do usuário são geridas no
   quadro (via skill `tarefas`), criar `tasks-go-to-board.md` (frontmatter `name/description/metadata.type: feedback`;
   corpo curto com o link do quadro, **Why** e **How to apply**) e a linha no `MEMORY.md`. Já existindo uma
   equivalente, não duplicar.
2. **Varrer conflito.** `grep -il` nas memórias dessa pasta pelo nome do gestor de `config/gestor` e por outras
   ferramentas de tarefas; as que mandarem tarefa ou pendência para outro destino → corrigir a linha, ou, se não
   ficar claro, avisar em UMA linha. Memórias sobre projetos/pauta que não falam de tarefa ficam como estão.
3. Silêncio quando nada mudou; se criou ou corrigiu algo, uma linha.
Sem a preferência (ou `false`): não mexer na memória.

## 1. Primeira mensagem da conversa (quando o hook pedir)
O hook injeta `[tarefas] primeira mensagem…`. Fazer ANTES de responder ao pedido, em poucas
chamadas paralelas, e sem atrasar a resposta com explicações:

1. Para cada URL do atalho local (`quadros.py listar`), em paralelo: `ArtifactData get config/preferencias` e
   `get indice/ativos`; junto, a conversa: com `get_session` (`"self"`, só no app desktop) → `sessionId`, `title`, `cwd`
   e o link `claude://claude.ai/epitaxy/<sessionId>`; sem ela (CLI) → do aviso do hook: `sessao=<id>` vira o id
   `cli:<id>` (chave `conversa:cli:<id>`, `link: null`, `retomar: "claude --resume <id>"`), `cwd=` a pasta, e o título
   é a primeira mensagem. Exatamente um quadro respondeu → é ele. Nenhum ou mais de um → `ACHAR-QUADRO.md` § Busca
   completa (inclui o desempate pelo `principal`) antes de escrever.
2. **Pular** (sem escrever nada, sem dizer nada) quando:
   - `card_por_conversa.ativo` é `false`;
   - o título da sessão ou a primeira mensagem contém algum item de `ignorar_titulos`, ou o `cwd` está em `ignorar_cwd`;
   - é uma execução de rotina agendada, um subagente, ou a conversa só pede `/bom-dia`, `/boa-noite` ou `/tarefas`;
   - a mensagem é trivial demais para virar tarefa (uma pergunta factual de uma linha, "oi").
2b. **Aberta por tarefa sugerida?** A primeira mensagem tem `Card do quadro: <id>` → ligar direto a esse card (sem
   procurar análogo), com `papel: "executor"` se ela cita uma `Conversa original`, senão `papel: "original"`. Seguir a
   regra de comunicação do prompt: com original, perguntas e resultado vão para lá por `send_message`.
3. **Já ligada?** Algum item do índice tem `k` contendo a chave desta conversa (`conversa:<sessionId>` ou
   `conversa:cli:<id>`) → não fazer nada.
4. **Procurar análogo** no índice, comparando a primeira mensagem com `t`, `p`, `tags` e `k` de
   cada item com `s` diferente de `feito`/`apagada`/`arquivada`:
   - Chave externa citada na mensagem (ABC-123, PR #356, nome de repo + issue) que esteja em `k` → é ela.
   - Mesmo assunto (mesmo projeto/pessoa/tema e mesmo objetivo) → é ela.
   - Só o projeto em comum não basta: projeto igual + objetivo novo = tarefa nova com `pai` ou tag do projeto.
5. **Modo `perguntar`** (`card_por_conversa.modo`): NÃO gravar nada agora. Montar a proposta do passo 6 (ligar ao
   card achado, ou card novo com título e projeto) e perguntá-la na linha de aviso do passo 8, em uma frase
   ("📌 Quadro: ligo esta conversa a "<título>"? / crio "<título>" na Entrada?"). Gravar só depois do sim, pelo
   passo 6; "não" → nada, e a pergunta não volta nesta conversa.
6. **Escrever** (modo `criar_e_avisar`, ou o sim do modo `perguntar`; um `batch`):
   - **Achou uma** → `update` na tarefa: acrescentar a conversa em `conversas` (formato de `SCHEMA.md` § `tasks`) e a
     chave dela em `chaves`; se estava em `entrada` ou `a_fazer`, mover para `fazendo`; linha no `historico`
     (`por: "tarefas"`); `update` no índice. Precisa da `version` da tarefa: fazer `get` dela antes.
   - **Não achou** → conferir que o id está livre (não existe no índice, nem como `apagada`/`arquivada`, e um `get`
     em `tasks/<id>` volta vazio; senão acrescentar `-2`, `-3`…) e fazer `set` de uma tarefa nova em `entrada`, `auto: true`, `fonte: {tipo: "conversa", ref: <id da conversa>}`, `area` = `area_padrao`,
     título curto tirado do pedido (não do título automático da sessão), `projetos` (um ou mais; o principal primeiro,
     `projeto` = ele, uma tag `projeto:<slug>` por projeto) e `tags` inferidos usando de preferência valores de
     `tags_conhecidas`, a conversa já ligada; `update` no índice (com `p` e `ps`). O `cwd` da sessão numa pasta de
     `config/projetos` (`SCHEMA.md` § `config/projetos`) já diz o projeto principal; um `get config/projetos` junto das
     leituras do passo 1 basta.
   - **Dúvida entre 2+ candidatas** → ligar à mais provável e citar a outra na linha de aviso.
7. **Nome curto da conversa** — só onde existe `set_session_title`, só em conversa NOVA (esta é a primeira mensagem),
   só se `titulo_conversa.automatico` for `true` e o id não estiver em `titulo_conversa.manter`. Nunca renomear sozinha
   uma conversa que já existia (o usuário reconhece pelo nome). `set_session_title` com `"self"`. **1 a 3 palavras**
   (até `titulo_conversa.max`, padrão 25 caracteres), no idioma do quadro: o assunto com a palavra que o usuário
   reconhece (PR, cliente, pessoa, tela). Sem o nome do projeto (a pasta e o quadro já dizem), sem `·`, sem data, sem
   emoji, sem verbo genérico. Ex.: `PR 42 checkout`, `Importação CRM`, `Onboarding deck`.
   Se o usuário já deu um nome à conversa, o app pede aprovação: tudo bem, ele decide.
8. **Avisar em UMA linha**, no topo da resposta, no idioma do quadro:
   `📌 Quadro: liguei esta conversa a "<título>".` ou `📌 Quadro: novo card "<título>" na Entrada (#<projeto>).`
   No modo `perguntar`, essa linha é a pergunta do passo 5.

## 2. Ao longo da conversa
Registrar só marcos, não cada passo (no máximo ~3 escritas por conversa):
- PR aberto/mergeado, deploy, entrega pronta → `historico` + `links` (PR) + `chaves` (`pr:<repo>#<n>`).
- Bloqueado esperando alguém → `status: esperando`, `proximo_passo` dizendo o quê e de quem, tag `pessoa:`.
- Decisão tomada → `historico` + `contexto` (uma linha com a decisão e o porquê).
- A tarefa passou a valer para mais de um projeto → acrescentar em `projetos` (o principal fica primeiro) e a tag
  `projeto:<slug>`; índice com `ps`.
- Virou outra coisa / é um projeto novo → criar a tarefa-mãe e pôr esta como `pai`, ou ligar com `relacionadas` (sempre nos dois lados).
- **Nunca** mover para `feito` sozinha: concluir é da skill `fechar` (pedida pelo usuário, ou sugerida pelo agente com
  pergunta antes), do `/boa-noite`, ou do usuário, se ele pedir aqui.

## 3. Pedidos diretos
- **registrar `<texto>`** → como o passo 6 acima, mas sem `auto` (pedido explícito: vale em qualquer modo).
- **buscar `<texto>`** → ler o índice e responder com os ids/títulos/status que batem; ler a tarefa inteira só da escolhida.
  Para filtros exatos no banco, `ArtifactData query` em `tasks` com `["tags","array-contains","pessoa:ana"]`,
  `["status","==","esperando"]` ou `["chaves","array-contains","linear:ABC-123"]`.
- **"cria/atualiza isso no <gestor>"** → `config/gestor` + receita `<skills>/tarefas/referencias/gestores/<tipo>.md`
  (no `generico`, a `receita` gravada no próprio `config/gestor`),
  com as `regras` dele e a regra da relação (`SCHEMA.md` § Quadro × gestor: card com `pai` não vai; buscar antes de
  criar em todos os status). Modo por operação: criar segue `escrever.criar`, editar segue `escrever.editar`
  (`propor_no_boa_noite` ou `sob_pedido` → pode, a pedido; `nunca` → dizer que está desligado). Gestor pendente → não
  escrever e sugerir `/quadro-tarefas gestor`. Mostrar o que vai
  ser escrito, escrever depois do ok e gravar a chave `<prefixo_chave>:<ID>` + link no card.
- **ligar / status / prazo / próximo passo** → `get` da tarefa (para a `version`) → `update` com `if_version` → índice.
- **"toda semana/todo mês eu faço X", "cria uma recorrente"** → `set` em `recorrentes/<id>` (`SCHEMA.md` § recorrentes),
  com `ultima` = véspera do `inicio` para a primeira ocorrência nascer na data; confirmar a regra em uma linha
  ("↻ toda segunda, aparece no quadro no dia"), datas no fuso do quadro. O card nasce quando o quadro abrir ou no
  próximo `/bom-dia`.
- **"essa conversa não precisa de card"** → apagar o card `auto` criado agora (`delete` + índice `s: "apagada"`)
  e, se for um padrão, acrescentar em `card_por_conversa.ignorar_titulos`.

## 4. Preferências
Quando o usuário corrigir um comportamento ("não cria card pra pesquisa rápida", "me pergunta antes de criar card",
"o projeto X é da área Y", "não renomeia minhas conversas"), gravar em `config/preferencias` (o campo certo de
`SCHEMA.md` § `config/preferencias`, ou `notas`) e dizer em uma linha que ficou registrado. Ler as preferências antes de
cada escrita da sessão.

## Como escrever (ArtifactData)
- Documento existente: sempre `if_version` com a versão lida. Conflito → reler e refazer, nunca forçar.
- Mais de 2 documentos → `batch` (uma aprovação, atômico). Ex. de ligação nova:
  ```
  writes: [
    {op:"update", collection:"tasks", doc_id:"site-pr-356", if_version:3,
     data:{conversas:[...antigas, nova], chaves:[...antigas, "conversa:<id>"], status:"fazendo",
           historico:[{em, texto:"Conversa ligada: <título>", por:"tarefas"}, ...antigas].slice(0,50),
           atualizado_em}},
    {op:"update", collection:"indice", doc_id:"ativos", if_version:<v>,
     data:{itens:{"site-pr-356":{t,s,p,ps,tags,k,pai,u}}, atualizado_em}}
  ]
  ```
- Arrays são substituídos inteiros no `update`: sempre mandar a lista completa (antigas + nova).
- Ids novos: `kebab-case` ASCII do título (até 40 caracteres; título sem letras latinas → `t-<hash curto>`), ou a chave
  externa quando houver uma só.

## Anti-patterns
- ❌ Escrever num quadro que não respondeu nesta sessão, ou escolher o quadro pelo nome do app, pela pasta ou por `CLAUDE_CONFIG_DIR`.
- ❌ Criar card sem antes procurar no índice; duplicar uma tarefa que tem a mesma chave.
- ❌ Mover para `feito` por conta própria; apagar tarefa que não foi criada nesta conversa sem o usuário pedir.
- ❌ Explicar o quadro na resposta: é uma linha de aviso e segue o trabalho.
- ❌ Escrever no gestor de tarefas fora do que `config/gestor.escrever` permite e sem o usuário pedir aquela escrita.
- ❌ Gravar o card no modo `perguntar` antes do sim.
- ❌ Gravar segredo, token, senha ou dado de cartão em qualquer campo.

---
name: boa-noite
description: >
  Rotina de FECHAR o dia do usuário, num escopo só, o do quadro de tarefas da conta do Claude. O quadro
  (artefato com banco) é a memória: subagentes resumem o que aconteceu em cada conversa do dia, o resumo entra
  no histórico do card certo, e a proposta (fechar, mudar de coluna, arquivar conversa) vai em blocos por
  projeto e só é gravada depois do ok. Fecha o diário do dia em dias/<hoje> no quadro, com o plano da manhã
  ticado, e arruma o índice. Trigger whenever the user says "boa noite", "boa noite claude", "fechar meu dia",
  "fechar o dia", "terminar o dia", "registrar o que fiz hoje", "encerrar o dia", "fechar o expediente", or
  invokes /boa-noite. "/boa-noite faxina" revisa as tarefas zumbis. Também propõe o que criar ou editar no gestor de
  tarefas da pessoa (o de config/gestor). (English: "good night", "close my day", "wrap up my day".)
user_invocable: true
argument-hint: "(nenhum) | faxina — revisar tarefas paradas há muito tempo | <escopo> (só confere)"
---

# boa-noite — fechar o dia

`<skills>` = a pasta-mãe do Base directory desta skill (funciona numa pasta de skills e dentro do plugin). Ex.:
`sh <skills>/tarefas/py <skills>/boa-noite/conversas.py ...`, `<skills>/tarefas/ACHAR-QUADRO.md` (o § 0 diz o caminho
alternativo de cada ferramenta do app desktop que faltar, como no CLI).

Objetivo: o que terminou sai da frente do usuário **com registro do que aconteceu**, o quadro reflete o dia, e
nada pendente é mexido sem ele. Par do `/bom-dia`, que abre o dia a partir do mesmo quadro.

**Contrato:** coletar → resumir (subagentes) → cruzar com o quadro → propor em blocos por projeto → gravar só depois
do ok → diário.

**Idioma, data e fuso:** o relatório, as propostas, os resumos e o diário no idioma de `config/preferencias.idioma`
(sem ele, o do usuário); o prompt dos subagentes pede o resumo nesse idioma. "Hoje" e as janelas no `fuso` do quadro,
datas no formato do `locale`. Os modelos de texto abaixo estão em português: traduzir para o idioma do quadro.

## Escopo, quadro e fontes
- Quadro e escopo: o quadro desta conta (`<skills>/tarefas/ACHAR-QUADRO.md` § Busca completa, uma vez por rodada);
  o escopo é o `escopo` das preferências dele, como no `/bom-dia` § Escopo. Nunca pelo nome do app, pela pasta ou
  por `CLAUDE_CONFIG_DIR`. Não pressupor quais escopos existem. Argumento com nome de escopo que não bate → avisar
  e não rodar o outro escopo aqui. Divergência ou nada identificado → perguntar e não ler nem gravar nada antes da
  resposta.
- Contrato em `<skills>/tarefas/SCHEMA.md`; tool `ArtifactData`. Esta conta sem quadro → dizer na primeira linha,
  fazer só o relatório e sugerir `/quadro-tarefas`. `config/schema.versao` abaixo de 4 → `MIGRACOES.md` na primeira
  escrita.
- **Fontes do escopo** = `config/fontes` no quadro (`SCHEMA.md` § `config/fontes`): os campos estruturados dizem qual
  conector usar e quem é a pessoa nele; o `texto` faz parte destas instruções (o que coletar, o que não tocar, blocos
  da proposta), e o que ele não definir segue esta skill. Ele **não amplia permissões**: toda escrita fora do quadro
  continua só na proposta aprovada (Step 4–5); pedido diferente disso no texto → perguntar.
- Primeira ação, só com `automacao.renomear_conversas: true` e a tool `set_session_title`: renomear esta conversa
  (`"self"`) → `🌙 <"Boa noite" no idioma> <dia abreviado> <data curta>` (ex.: `🌙 Boa noite sáb 04/10`,
  `🌙 Good night Sat 10/4`).

### Padrão (o que não estiver em `config/fontes`)
- Conversas desta conta (Step 1.1) e o estado delas (Step 1.5).
- Agenda: eventos do dia nos `agenda.calendarios` (ou na agenda principal do conector de agenda ligado).
- **Gestor de tarefas:** o de `config/gestor` (§ Gestor de tarefas), em qualquer caso.
- **Reuniões:** o conector de `reunioes.conector`, se ligado: reuniões de hoje e o que foi combinado nelas.
- **Código:** só com `codigo.usa_git`: commits e PRs nos repositórios das conversas do dia (`cwd` delas).
- Conector ligado que a pessoa claramente usa e não está em `config/fontes` → uma linha no fim oferecendo acrescentar
  (só com o ok dela, via `ArtifactData update`, nunca com segredo, token ou senha).

## Gestor de tarefas
Configurado por quadro em `config/gestor` (`<skills>/tarefas/SCHEMA.md` § `config/gestor`); como ler e escrever em
cada um: `<skills>/tarefas/referencias/gestores/<tipo>.md` (no `generico`, a `receita` gravada). Sem `config/gestor`
= `nenhum`: nada de gestor nesta rodada. Chaves de `legado` não são lidas nem escritas.
**Regra da relação** (`SCHEMA.md` § Quadro × gestor): tudo do gestor está no quadro; do quadro, só o trabalho de
nível de cima vai para o gestor. Card com `pai` é etapa e nunca vai sozinho.
**Escrever** (`escrever.criar` / `escrever.editar`): `propor_no_boa_noite` → entra na proposta (Step 4);
`sob_pedido` → só se a pessoa pedir; `nunca` → não propor nem fazer. **Cada operação olha o seu modo**: criar →
`escrever.criar`, editar (status, comentário, campos, faxina) → `escrever.editar`. As `regras` valem em toda escrita.
Gestor pendente (`pendente: true` ou sem o § Obrigatório da receita) → nada de gestor nesta rodada; uma linha no
relatório sugerindo `/quadro-tarefas gestor`.

## Passos

### Step 0 — Quadro, fontes e plano da manhã (paralelo)
`ArtifactData get config/preferencias`, `get config/fontes`, `get config/gestor`, `get indice/ativos`, `get dias/<hoje>` (e, para "dias
sem rodar", `list dias` para achar o último `boa_noite`). O `bom_dia.plano` de hoje é o "Hoje era"; cada item vira `x` (feito), `~` (andou) ou ` ` (não andou). Sem
plano: usar o `foco_amanha` do último fechamento.

**Dias sem rodar:** se pedir para cobrir dias sem `/boa-noite`, a janela começa no dia seguinte ao último
`boa_noite` em `dias/`; uma entrada só, com `cobre: [datas]`.

### Step 1 — Evidência do dia (paralelo, só leitura)
1. **Conversas → texto novo:** `sh <skills>/tarefas/py <skills>/boa-noite/conversas.py extrair --sessao <id desta conversa> --quadro <id do artefato> --saida <scratchpad>/conv --desde <início da janela> --fuso <fuso>`
   (`--sessao` = o `sessionId` de `get_session "self"` no app, que limita às conversas desta conta; no CLI, `cli:<id>`
   do aviso do hook. `--backend auto` escolhe sozinho entre as conversas do app e os transcritos locais;
   `config/fontes.conversas.backend` fixa a escolha. Sem quadro, omitir `--quadro`; sem `fuso`, omitir `--fuso`.)
   Gera, por conversa, um ou mais `.txt` (`arquivos`, partes de até 14 mil caracteres, nada cortado) só com o
   trecho ainda não resumido (cursor por conversa) e `manifesto.json` (id, título, rotina, repetida, link,
   `cursor_perdido`, `primeira_leitura`). Conversa aberta que nunca foi resumida entra **inteira**, seja qual for a
   data (`primeira_leitura: true`): rodada pulada ou janela curta não escondem conversa (nos transcritos, só as com
   atividade na janela, para não ler o histórico inteiro na primeira rodada). `--desde` só vale para
   `cursor_perdido`. `cursor_perdido: true` = o transcript foi reescrito e o trecho veio pela data: avisar
   o subagente que pode haver repetição do que já está no histórico do card. Rotina repetida (`repetida: true`) não é
   resumida: entra direto como "arquivar".
2. **Código** (só com `codigo.usa_git`): PRs mergeadas e commits do dia nos repositórios das conversas e de
   `config/fontes.codigo`. Commits: `git -C <repo> log --since="<data> 00:00" --all --oneline`.
3. **Gestor de tarefas:** itens da `leitura` (padrão: atribuídos à pessoa) que mudaram na janela (receita do tipo) e, para cada card aberto
   com chave do gestor que não veio aí e está em Fazendo/Esperando ou citado hoje, o estado atual do item. Outras
   tarefas externas, conforme as fontes.
4. **Reuniões:** eventos do dia nas agendas do escopo; transcrição no conector de `reunioes` quando houver.
5. **Estado das conversas:** com `list_sessions` (`limit: 200`): `isArchived`, `prState`, branch. Sem ela: o que o
   manifesto traz (`cwd`, `branch`) e, com `codigo.usa_git`, o estado do PR pelo conector de código ou `gh`.
6. **Fechadas durante o dia pela skill `fechar`:** `dias/<data>.fechados` de cada dia da janela. Essas conversas já
   estão arquivadas e com o card atualizado: entram no relatório e no diário com o resumo do `fechar`, **sem** subagente e
   sem nova proposta. Só olhar de novo se o transcript tiver atividade depois do `em` do fechamento (a conversa foi
   reaberta): aí rodar o `extrair` com `--incluir-arquivadas` só para ela e tratar como conversa comum.
   Cruzar com o resto do dia: o resumo do `fechar` pode completar outro card (mesmo projeto, pessoa ou chave) ou
   explicar uma reunião; isso entra na proposta como qualquer evidência.

### Step 2 — Resumir com subagentes
Disparar subagentes (Agent tool, `general-purpose`) com `model` = `config/preferencias.resumo.modelo` (`null` ou
ausente = não passar `model`: vale o padrão de subagente da sessão), em paralelo, cada um com 1–6 conversas do
manifesto (todas as partes de uma conversa no mesmo subagente; até ~40 mil caracteres por subagente). Sem a tool de
subagentes: resumir aqui mesmo, em lotes. Prompt de cada um (preencher, no idioma do quadro):

> Você resume conversas de trabalho para um quadro de tarefas. Para cada arquivo, leia o texto e devolva
> SÓ um array JSON, um objeto por conversa:
> `{"id", "projeto", "o_que_foi_feito": "1–3 frases, fatos", "decisoes": ["decisão — porquê"],
>   "artefatos": ["PR #n repo", "commit abc123", "arquivo/URL"], "pendencias": ["o que falta e de quem depende"],
>   "estado": "entregue|em_andamento|esperando_usuario|esperando_terceiro|abandonada",
>   "acao": "arquivar|manter", "motivo_manter": "só se manter: risco concreto",
>   "tarefa_sugerida": "id do índice que bate, ou null", "titulo_tarefa": "se não bate nenhuma, título curto",
>   "tags": ["pessoa:x", "tema:y"]}`
> Regras: não invente nada que não está no texto. "manter" só com risco concreto: trabalho rodando, entrega
> principal por fazer<com codigo.usa_git: , commit sem push, PR aberto>. "entregue" só com evidência explícita no
> texto (o usuário disse que terminou, a entrega foi feita e confirmada<com codigo.usa_git: , PR mergeado>). Uma
> oferta no fim ("quer que eu…?") não segura a conversa. Responda no idioma: <idioma>.
> Índice do quadro (id → título · projeto · tags): <colar as linhas abertas do indice/ativos, ~1 linha cada>.
> Regras extras do usuário (valem acima das de cima): <colar regras_fechamento, ou "nenhuma">.

Juntar os JSONs. Reportar no fim: quantos subagentes, o modelo, tokens de entrada/saída e custo estimado em USD
(do uso que os subagentes devolvem; sem o número, dizer "custo não informado"). Antes de rodar com mais de
`resumo.confirmar_acima` subagentes (padrão 15), confirmar com o usuário.

### Step 3 — Cruzar com o quadro
Para cada resumo:
- **Tarefa:** `tarefa_sugerida` confirmada pela chave `conversa:<id>` ou pelo assunto → atualizar esta. Sem
  tarefa e com trabalho real → propor criar (via regras da skill `tarefas`). Pesquisa avulsa/rotina → só diário.
- **Coluna proposta:** `entregue` → `feito` (com evidência: "feito" do usuário, entrega confirmada; com git, PR
  mergeada ou deploy);
  `esperando_terceiro` → `esperando`; `em_andamento` → `fazendo`; `abandonada` → perguntar (descartar?).
- **Conversa** (só com `automacao.arquivar_conversas: "propor"` e a tool `archive_session`; senão, nenhuma linha
  🗄️ e o relatório só diz quais acabaram): `acao` do resumo, conferida antes de arquivar. Com `codigo.usa_git` e a
  conversa num repositório: `git status` da pasta dela (ignorando `codigo.ruido`) e
  `git log <remoto>/<base>..HEAD` (`codigo.remoto`, `codigo.branch_base`; base `null` = a branch padrão do remoto).
  Arquivo novo fora do git numa worktree → com `codigo.copiar_fora_do_git`, copiar para o mesmo caminho no checkout
  principal (sem sobrescrever; se existir diferente, perguntar); sem ela, ⏸️ com o motivo. Commit sem push → não
  arquivar. PR aberto → não arquivar.
- **Varredura das abertas (toda rodada, sem subagente; só no app, com `list_sessions`):** toda conversa não arquivada
  que não veio no manifesto (já resumida antes, sem texto novo) volta à proposta com evidência barata: `prState` e,
  com git, `git status` e o `git log` acima. PR mergeado/fechado → 🗄️; PR aberto ou commit sem push → ⏸️ (com o
  porquê); parada há 3+ dias sem nada pendente → 🗄️ com o motivo; sem como saber → ❓. Fora da varredura: esta
  conversa, a execução mais recente de cada rotina, as de `titulo_conversa.manter` e as de `notas` que mandam manter
  aberta.
- **Ocorrências de recorrentes** (cards com `recorrente`): fecham como qualquer tarefa, com evidência. A de hoje ainda
  aberta → ❓ "fez <título> hoje?" (sim → ✅; não → fica, e o `/bom-dia` de amanhã a mostra atrasada). Nunca apagar,
  nem mexer em `recorrentes/`.
- **Tarefas do quadro sem conversa hoje:** fechar só com evidência explícita das outras fontes (item fechado no
  gestor, reunião que registrou a entrega; com git, PR). Sem evidência, a tarefa fica, a não ser que uma regra de
  `regras_fechamento` cubra o caso (ex.: "data que passou há semanas sem registro: presumir que aconteceu") — aí
  propor fechar citando a regra.
- **Gestor → quadro:** item do gestor que veio no Step 1.3 sem card com a chave dele → como o `/bom-dia` Step 1b
  (análogo claro → ligar; dúvida → ❓; nada → `🆕`; depois, os `pai`). Item que já chegou concluído e nunca teve card
  → `🆕` direto em `feito` (só espelha o gestor). Item **concluído** no gestor → `✅ Fechar` o card
  (`resolucao: "concluida"`); **cancelado ou duplicado** → `✅ Descartar` (`resolucao: "descartada"`). Essas mudanças
  só espelham o gestor: não geram 📤.
- **Filhos de um item do gestor:** todos os filhos de um card com chave do gestor concluídos (ou indo para concluído
  nesta proposta) = evidência de que o pai pode fechar → propor ✅ Fechar no pai e 📤 no item. Filhos todos descartados
  não fecham o pai: ❓.
- **Quadro → gestor (upsert), conforme `escrever.*`:** para cada card de nível de cima (sem `pai`) que mudou hoje ou
  vai mudar nesta proposta:
  - **Tem chave do gestor** (`escrever.editar`) → 📤 **editar**. Status alvo pela coluna proposta **e pela
    resolução**: `feito` + `concluida` → `mapa_status.feito`; `feito` + `descartada` → `mapa_status.descartada`;
    demais colunas → o mapa delas (`null` = não mexe). Comentário curto no idioma da pessoa, sem citar o Claude
    ("Concluído em <data>: <o que foi entregue>" ou "Descartado em <data>: <motivo>"); título/descrição só se o escopo
    mudou no dia. **Nunca ecoar o gestor:** item já **exatamente** no status alvo (comparar o nome do status, não o
    tipo/categoria: `In Progress` → `Blocked` é mudança), ou mudança do card que veio do próprio item (Gestor →
    quadro, acima) → nenhum 📤 de status. Comentário e título/descrição são avaliados à parte.
  - **Sem chave do gestor nem de `legado`**, trabalho de verdade (não pessoal, não trivial, não pesquisa avulsa, não
    rotina) → antes, buscar no gestor em **todos os status** (receita: busca por texto) e separar:
    mesmo item aberto → 📤 **ligar** e editar o que precisar (`escrever.editar`); mesmo item já fechado → 📤 **ligar**
    e ✅ fechar o card pela resolução do item (sem reabrir, sem escrever no item); nenhum → 📤 **criar**
    (`escrever.criar`). Na dúvida entre ligar e criar → ❓.
  - **Só com chave de `legado`** → nunca 📤 criar. Buscar no gestor (título e a chave antiga): achado claro → 📤
    **ligar**; senão nada (o card fica só no quadro).
  - Card criado nesta rodada (🆕) entra no mesmo upsert.
  - Card com a tag `gestor:fora` não é proposto. A pessoa recusou um 📤 criar ("esse fica só no quadro") → gravar
    essa tag no card, para não propor de novo.
  - Aplicar `regras` (labels, projeto, o que nunca criar) e montar o texto exato que vai ser escrito.

### Step 4 — Proposta (uma mensagem, sem AskUserQuestion)
Blocos por projeto (o `projeto` das tarefas, que é o principal: card em vários projetos aparece só no bloco do
principal, com os outros entre parênteses; nomes, ordem e emojis dos blocos: os que `config/fontes.texto` definir,
senão o nome do projeto e "Sem projeto" por último), cada linha com a ação na frente:
- `✅ Fechar <tarefa>` (concluída) ou `✅ Descartar <tarefa>` (cancelada) — evidência em meia linha;
- `➡️ <coluna> <tarefa>` — por quê;
- `🆕 Criar <título>` (#projeto, tags) — de qual conversa;
- `🗄️ Arquivar <conversa>`; execuções de rotina agrupadas numa linha por rotina;
- `✏️ Renomear` (só com `automacao.renomear_conversas: true` e a tool `set_session_title`) — numa linha só, as
  conversas que **ficam abertas** com título acima de `titulo_conversa.max` (padrão 25) caracteres ou confuso
  (`antigo → novo`), menos as de `titulo_conversa.manter` e as que o usuário já nomeou e reconhece (na dúvida, não
  propor). **1 a 3 palavras**, no idioma do quadro, o assunto com a palavra que o usuário reconhece (PR, cliente,
  pessoa, tela). Sem o nome do projeto, sem `·`, sem data, sem emoji, sem verbo genérico. Ex.: `PR 42 checkout`,
  `Proposta Acme`. Rotinas agendadas e bom-dia/boa-noite não entram nessa regra.
- **Bloco `📤 <config/gestor.nome>`**, numerado, por último: `📤1 Editar ABC-123 → Done · "Concluído em <data>: …"`,
  `📤2 Criar "<título>" (labels, projeto, cycle) ← card <id>`, `📤3 Ligar card <id> → ABC-124 e mover para In Progress`.
  Uma linha por item, com o que vai ser escrito de fato;
- `❓ N` — dúvida real e rara, com o motivo;
- `⏸️ Manter` — só com risco concreto (roda ainda, entrega por fazer; com git, commit sem push ou PR aberto).
Terminar pedindo resposta curta: "ok" aprova ✅ ➡️ 🆕 🗄️ 📤 e deixa os ❓ como estão; "ok sem 📤" ou "ok menos 📤2"
tira escritas no gestor.

### Step 5 — Gravar (depois do ok)
Num ou mais `ArtifactData batch` (cada tarefa existente com o `if_version` lido):
- **Tarefa atualizada:** linha no `historico` com o resumo do dia (`por: "boa-noite"`), `resumo` (estado atual em
  1–2 frases), `links`/`chaves` dos artefatos (PRs, commits), `conversas[].arquivada` quando arquivar, status novo;
  `feito` → `resolucao` da linha aprovada (`✅ Fechar` → `"concluida"`; `✅ Descartar` → `"descartada"`), `concluido_em`.
- **Tarefa criada:** modelo do SCHEMA, com a conversa ligada e o resumo no histórico.
- **Arquivo do mês (antes do índice):** feitas há mais de `arquivar_feitas_dias` → entrada em `arquivo/<AAAA-MM>`
  (merge) e só depois `delete` da tarefa.
- **Índice (por último):** `get indice/ativos` (guardar a `version`) → `list tasks` com `out_dir` → montar `itens`
  com todas as tarefas de `tasks` (formato de `SCHEMA.md` § `indice/ativos`, com `ps` = `projetos` ou `[projeto]`) e manter como `{"s": "apagada"|"arquivada"}` os ids que já estavam marcados assim
  (ids não se reaproveitam) → `set` com `if_version`. Conflito (a página ou outra conversa escreveu no meio) → refazer
  as três etapas; nunca forçar.
- **Gestor (📤 aprovados):** pela receita do tipo, um item por vez. Criado ou ligado → gravar no card a chave
  `<prefixo_chave>:<ID>` e o link (no mesmo `batch` das tarefas, ou num `update` logo depois). Falhou → o card fica sem
  a chave e o relatório diz qual.
- **Outras ferramentas:** só o que as fontes do escopo mandam e só o que estava na proposta aprovada.
- **Nomes:** `set_session_title` com o `sessionId` de cada `✏️` aprovado (e o mesmo título curto em
  `conversas[].titulo` no card).
- **Conversas:** `archive_session` nas aprovadas. Negado pelo app → listar no relatório para arquivar pela barra lateral.
Escrita que falhar: seguir com as outras e dizer no relatório o que não foi gravado.

### Step 6 — Diário e relatório
`dias/<hoje>` (`update` com `if_version` se o `bom_dia` já existe; `set` se não existe) com `boa_noite`:
`gerado_em`, `cobre`, `plano` (itens da manhã com `marca`), `fechado`, `pendente`, `foco_amanha` (1–2 ids),
`conversas` (id, título, resumo, tarefa, ação; as do `fechar` com `acao: "fechada_no_dia"`) e `custo` dos subagentes
(`modelo`, `subagentes`, tokens, `usd`).
Relatório curto no chat (formato das fontes, se definirem; senão este):
```
🌙 Fechamento (<escopo>) — <data>
Hoje era:
- [x] … / - [~] … / - [ ] …
Fechado: … (evidência)
Quadro: N atualizadas · N criadas · N movidas
Gestor: N editados · N criados · N ligados  (só se houver)
Arquivado: …
Fechadas no dia (fechar): N — <título curto · resultado>, …
Intocado: N pendentes (e conversas mantidas, com o porquê)
Resumo: N subagentes (<modelo>) · X tokens in / Y out · ~US$ Z
```
Depois que `dias/<hoje>` foi gravado: `sh <skills>/tarefas/py <skills>/boa-noite/conversas.py confirmar --quadro <id do artefato, ou omitido se não há quadro> --manifesto <scratchpad>/conv/manifesto.json --ids <ids>`
só com as conversas cujo resumo entrou no quadro (as que falharam ficam para a próxima rodada).
Terminar com "boa noite" (no idioma do quadro).

## Modo `faxina`
Só quando o usuário pede. Na conta do escopo: tarefas do quadro paradas há `zumbi_dias`+ e itens do gestor atribuídos
à pessoa sem movimento há `zumbi_dias`+ (receita do tipo; fora os de `legado`), agrupados por projeto, com proposta em
lote: descartar (`feito` + `resolucao: "descartada"`; no gestor, status `mapa_status.descartada` com o comentário
"Fechado na limpeza de backlog de <data>", se `escrever.editar` não for `nunca`), reatribuir ou manter. Confirmação
antes de gravar.

## Preferências
Correções do usuário sobre como fechar ("isso não é tarefa", "rotina X não precisa de resumo", "pode arquivar
conversa de pesquisa") vão para `config/preferencias` (`regras_fechamento`, `card_por_conversa.ignorar_titulos`,
`automacao.*` ou `notas`). Ler antes de cada rodada.

## Anti-patterns
- ❌ Misturar escopos ou gravar no quadro/diário de outro escopo.
- ❌ Gravar qualquer coisa antes do ok da proposta, ou mostrar a proposta sem blocos por projeto.
- ❌ Mudar coluna, comentar ou preencher campo de tarefa pendente sem estar na proposta aprovada.
- ❌ Fechar sem evidência verificável (ou sem uma regra de `regras_fechamento` que cubra o caso); o subagente sugere,
  a evidência decide.
- ❌ Passar resumo inventado: o histórico só leva o que está no texto da conversa ou nas fontes.
- ❌ Escrever no gestor fora de um 📤 aprovado (ou de um pedido, no modo `sob_pedido`), ou com o modo daquela operação
  (`escrever.criar` / `escrever.editar`) em `nunca`.
- ❌ Mandar ao gestor como Done o que foi descartado, ou devolver ao gestor uma mudança que veio dele.
- ❌ Propor criar no gestor novo um card que só tem chave de `legado`.
- ❌ Mandar card filho (com `pai`) para o gestor; criar item sem antes buscar se ele já existe lá.
- ❌ Pôr no gestor link `claude://`, trecho de conversa, dado pessoal ou menção ao Claude.
- ❌ Criar item em outra ferramenta externa, mandar mensagem a alguém, commitar, pushar ou mergear.
- ❌ Arquivar conversa com trabalho rodando, ou (com git) commit sem push, PR aberto ou arquivo fora do git sem copiar.
- ❌ Avançar os cursores antes de gravar no quadro.
- ❌ Gravar segredo, token ou senha em `config/fontes`, `config/gestor` ou em qualquer documento do quadro.

## Melhoria contínua
Aprendeu algo sobre o fluxo? Preferência do usuário → `config/preferencias`. Ferramenta, pessoa ou regra do escopo
→ `config/fontes` (com o ok do usuário). Mudança de processo que vale para todo mundo → este SKILL.md.

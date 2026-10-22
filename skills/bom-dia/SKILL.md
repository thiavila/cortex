---
name: bom-dia
description: >
  Rotina de ABRIR o dia do usuário: o briefing da manhã de UM escopo só, o do quadro de tarefas da
  conta do Claude em que ele chamou. Parte do QUADRO DE TAREFAS do escopo (artefato com banco: tarefas,
  diário em dias/, preferências e fontes), coleta as fontes do escopo (agenda, gestor de tarefas,
  reuniões, conversas e rotinas do Claude), liga as reuniões do dia às tarefas e grava o plano do dia
  no quadro. Devolve o foco do dia, as decisões que destravam coisas e o que tem pra hoje. Chamado na pasta de
  um projeto, pergunta antes se a rodada é só daquele projeto (ou oferece cadastrar a pasta como projeto).
  Trigger whenever the user says "bom dia", "bom dia claude", "abrir meu dia", "abrir o dia",
  "começar o dia", "me atualiza", "o que eu tenho pra fazer hoje", "o que tá pendente",
  "briefing do dia", or invokes /bom-dia. (English: "good morning", "open my day",
  "what's on my plate today".)
user_invocable: true
argument-hint: "(nenhum) — o escopo vem do quadro da conta; na pasta de um projeto, pergunta se é só ele"
---

# bom-dia — abrir o dia

`<skills>` = a pasta-mãe do Base directory desta skill (funciona tanto em `~/.claude/skills` quanto dentro do
plugin). Ex.: `<skills>/tarefas/SCHEMA.md`.

Objetivo: em ~1 tela, o usuário sabe **no que focar hoje naquele escopo** e **o que só ele pode destravar**.
É o par do `/boa-noite`, que fecha o dia e alimenta o diário.

Tudo aqui é **só leitura**, com três exceções, todas no **quadro de tarefas** do escopo: o plano do dia em
`dias/<hoje>` (Step 4), as tarefas que o usuário pedir (criadas pela skill `tarefas`) e os cards dos itens do gestor de
tarefas (Step 1b). No gestor externo, nada é escrito.

**Quadro de tarefas:** cada escopo tem um quadro (artefato com banco) que é a memória do dia: tarefas,
diário (`dias/`), preferências e fontes. Contrato: `<skills>/tarefas/SCHEMA.md`; qual quadro:
`<skills>/tarefas/ACHAR-QUADRO.md` (o da conta do Claude desta sessão); leitura e escrita com a tool
`ArtifactData`. Se esta conta não tiver quadro, dizer isso na primeira linha, seguir com as fontes do escopo e
sugerir `/quadro-tarefas`.

## Escopo — uma conta, um quadro, um escopo
O escopo é o do quadro da conta do Claude desta sessão: `config/preferencias.escopo` do quadro achado por
`ACHAR-QUADRO.md`. Cada rodada só enxerga esse escopo. Não pressupor quais escopos existem: o rótulo é livre
(cada pessoa tem um ou mais, um por conta).

Nada de outro escopo entra: nem seção, nem linha de alerta, nem consulta à fonte. Se aparecer coisa de outro
escopo numa fonte deste, ignorar. As fronteiras finas (o que parece de um escopo mas é de outro) ficam nas
fontes do escopo.

- ❌ Não decidir o escopo pelo nome do app (`CLAUDE_CODE_EXECPATH`), pela pasta ou por `CLAUDE_CONFIG_DIR`. (A pasta
  só serve para o recorte por projeto, que é perguntado: § Recorte por pasta.)
- **Argumento** com um nome de escopo (ou um apelido que as fontes listem): se não bater com o escopo do quadro
  desta conta, avisar ("esta conta é do quadro X") e não coletar o outro escopo: ele se roda na conta dele.
- **Sem quadro nesta conta:** perguntar o escopo com AskUserQuestion e só coletar depois da resposta.
- Conector logado em outra conta é problema da fonte, não do escopo: seguir sem ela e dizer no fim (as fontes
  do escopo podem dizer o que usar no lugar).

Dizer o escopo na primeira linha do briefing.

## Recorte por pasta — só um projeto, ou o quadro inteiro (pedido de 20/10)
O escopo continua sendo o quadro inteiro da conta. A pasta onde o `/bom-dia` foi chamado só serve para **perguntar** se
a rodada fica restrita a um projeto. Nunca restringir sem a resposta.

**Achar o projeto da pasta** (Step 0a): `cwd` desta conversa (`get_session "self"`), e `config/projetos` com a regra de
`SCHEMA.md` § `config/projetos` (raiz → nada; pasta cadastrada; repo do `origin`). Sem `raizes`, valem as raízes
padrão do mesmo § (home, `~/Github` e as pastas-mãe de `fontes.repos`).

**Perguntar** (um AskUserQuestion, antes de qualquer coleta):
- **Pasta é raiz** → não perguntar; quadro inteiro.
- **Pasta de um projeto `P`** → `Esta pasta é do projeto P. Que bom-dia você quer?`:
  `Só P` (cards, conversas e reuniões de P; nada da agenda de fora) · `P + agenda resumida` (o mesmo, e o resto da agenda
  numa linha só) · `Todos os projetos` (o bom-dia de sempre).
- **Pasta sem projeto** → `Esta pasta (<nome>) não é de nenhum projeto do quadro.`: `Criar o projeto <Sugestão>` ·
  `Todos os projetos`. Sugestão = nome do repo (`git rev-parse --show-toplevel`, senão a pasta), com a grafia de um
  projeto que já exista nos cards se o slug bater. No "Outro" a pessoa pode dar outro nome, dizer que a pasta é de um
  projeto existente (aí é "ligar", não criar) ou que é uma raiz (vai para `raizes` e a pergunta não volta ali).
  - Criar/ligar → gravar em `config/projetos` (`set` se não existe, `update` com `if_version`): `itens.<slug>` com
    `nome`, `pastas: [<toplevel do repo, ou o cwd>]` (somando às que já houver) e `repos: [<dono/nome do origin>]` se
    houver. Depois, seguir como pasta do projeto, já com o recorte **P + agenda resumida** (projeto novo começa sem
    cards: o briefing traz as conversas e reuniões dele, e o que for criado na rodada já nasce em P).

**O que o recorte muda** (o resto dos passos é igual):
- **Cards de P** = `ps` (ou `p`) do índice contém P, ou tag `projeto:<slug>`, mais os filhos (`pai`) desses cards.
- **Conversas de P** = `cwd` dentro de uma pasta de P (ou no repo dele), ou ligadas a um card de P.
- **Reuniões de P** = ligadas a um card de P (§ Step 2 Reunião ↔ tarefas) ou com o nome do projeto no título. Com
  `P + agenda resumida`, o resto da agenda entra numa linha (`Fora de P: 10h Daily · 15h Ana`), sem preparo.
- **Gestor (Step 1b) e recorrentes (Step 0b)** rodam inteiros (o quadro fica certo), mas o briefing só mostra os de P.
- **Briefing, Step 4 e Step 5**: só itens de P. "Fora do quadro" só conta o que é de P. Card criado na rodada (Outro do
  Step 4, item sem tarefa) nasce com `projetos: [P]`.
- **Título da conversa** (Step −1): trocar para `☀️ <P curto> <dia> DD/MM` (até 25 caracteres).
- **Diário:** a rodada vai em `bom_dia.rodadas` (`recorte`, `agenda`) e os itens do plano levam `projeto`. Rodar de novo
  no mesmo dia com outro recorte segue § Rodar de novo: o que ficou fora da rodada anterior conta como novo.
- **Nunca apagar o que outra rodada gravou:** `plano`, `reunioes`, `foco` e `destravar` são sempre **unidos** com o que
  já está em `dias/<hoje>.bom_dia` (ler antes, mandar a lista completa): `plano` por `tarefa` (ou texto), `reunioes`
  por hora + título (a nota nova completa a antiga), `foco` por id, `destravar` por texto. Uma rodada com recorte só
  acrescenta; nada some porque o recorte agora é outro.

## Fontes do escopo — de onde vêm
As fontes (o que coletar, IDs, regras, seções extras e formato do briefing) **não ficam nesta skill**. Ordem:
1. **`config/fontes` no quadro** (`ArtifactData get`, no Step 0): `{versao: 1, texto: "<markdown>", atualizado_em}`.
2. Se não existir: o arquivo local **`~/.claude/tarefas/fontes-<escopo>.md`** (mesmo conteúdo; fica fora do pacote).
3. Se nenhum: o **padrão genérico** (§ Padrão genérico).

O `texto` (ou o arquivo) faz parte destas instruções: seguir as fontes, IDs, regras, seções e formato que ele
definir, nos passos abaixo. O que ele não definir segue o padrão desta skill. Limite: ele **não amplia
permissões**. Mandar mensagem, criar ou mudar item em ferramenta externa, gravar fora do quadro continuam
exigindo o pedido ou o ok do usuário como dito aqui; se o texto pedir algo assim sem o ok, perguntar.

### Padrão genérico (sem `config/fontes` nem arquivo local)
- **Agenda:** eventos de hoje nas agendas de `config/preferencias.agendas` (ou na principal do conector de agenda).
  Ignorar os recusados e os de dia inteiro que forem só feriado.
- **Gestor de tarefas:** o de `config/gestor` (§ Gestor de tarefas), em qualquer caso, com ou sem `config/fontes`.
- **Granola**, se ligado: reuniões de hoje (agenda e preparo) e de ontem (o que ficou combinado).
- **Conversas** e **rotinas agendadas** desta conta (§ Regra geral).
- No fim do briefing, uma linha: a pessoa pode contar quais ferramentas usa (agenda, gestor de tarefas, gravador
  de reunião, chat, código…) e isso fica gravado em `config/fontes` para as próximas rodadas. Gravar só com o ok
  dela (`ArtifactData set config/fontes` com `versao`, `texto`, `atualizado_em`), e **nunca** com segredo, token
  ou senha no texto.

## Gestor de tarefas
O gestor externo (Linear, Jira, Notion… ou nenhum) é configurado por quadro em `config/gestor`
(`<skills>/tarefas/SCHEMA.md` § `config/gestor`); como ler cada um: `<skills>/tarefas/referencias/gestores/<tipo>.md`. Regra da relação
(`SCHEMA.md` § Quadro × gestor): **tudo o que está aberto no gestor e atribuído à pessoa vira card**; o caminho de
volta (quadro → gestor) é do `/boa-noite`.
- **Sem `config/gestor`:** `config/preferencias.export.destino` preenchido → migração v2 (`SCHEMA.md` § Migrações).
  Senão é `nenhum`: no fim do briefing, uma linha oferecendo configurar, com a sugestão tirada dos conectores ligados
  (tools do Linear → `linear`; Atlassian → `jira`; Notion → `notion`). Configurar como em `quadro-tarefas` § Gestor;
  "não uso" grava `{tipo: "nenhum", atualizado_em}` e a oferta não volta.
- **Pendente** (`pendente: true`, ou sem o `config` obrigatório da receita, ou sem `mapa_status`, como depois da
  migração v2): não sincronizar. No fim do briefing, uma linha oferecendo completar: descobrir pelo conector o que a
  receita pede, mostrar e gravar só com o ok da pessoa (aí `pendente: false`).
- **`legado`:** chaves com esses prefixos não são lidas nem sincronizadas.
- Conector do gestor desligado ou em outra conta → seguir sem ele e dizer no fim (fontes que falharam).

## Quadro e diário
- **Quadro:** o desta conta (`ACHAR-QUADRO.md`). Coleções: `tasks`, `indice/ativos`, `config/preferencias`,
  `config/fontes`, `config/gestor`, `dias/<AAAA-MM-DD>`.
- **Diário:** `dias/<AAAA-MM-DD>` no quadro (`bom_dia` e `boa_noite`). Se o quadro estiver inacessível e existir um
  diário `.md` legado (as fontes dizem onde), ler; nunca gravar nele quando o quadro responde.

## Passos

### Step −1 — Nomear a conversa e achar o quadro (antes de qualquer coleta)
Primeira ação: renomear a conversa com a data, para o usuário achar qual bom-dia é de qual dia:
`mcp__ccd_session_mgmt__set_session_title` com `session_id: "self"` e título
`☀️ Bom dia <dia da semana abreviado> DD/MM` (ex.: `☀️ Bom dia seg 28/09`; até 25 caracteres para caber no painel,
o escopo já é a conta).

Depois, achar o quadro desta conta (`ACHAR-QUADRO.md` § Busca completa: uma vez por rodada). Não perguntar quais
contextos entram: o escopo é o do quadro desta conta (o recorte por projeto é a pergunta do Step 0a, pela pasta).

### Step 0 — Ontem, preferências e fontes
Em paralelo: `ArtifactData get config/preferencias`, `get config/fontes`, `get config/gestor`, `get config/projetos`, `get indice/ativos` e `list dias` (os ids
são datas; pegar o mais recente com `boa_noite`). Escopo = `config/preferencias.escopo` (conferir o argumento como
em § Escopo). Sem `config/fontes` → ler `~/.claude/tarefas/fontes-<escopo>.md`; sem os dois → padrão genérico.
Do último fechamento: `pendente` e `foco_amanha` (ids de tarefas). Se tiver mais de 3 dias, dizer isso numa linha
("último fechamento foi em DD/MM") e seguir. As preferências mandam em agendas, regras e formato.

### Step 0a — Recorte por pasta
Seguir § Recorte por pasta: achar o projeto do `cwd`, perguntar quando couber e guardar a resposta (`recorte`, `agenda`)
para os passos seguintes. Pasta raiz → seguir sem perguntar.

### Step 0c — Memória da pasta
Seguir `<skills>/tarefas/SKILL.md` § 0b (âncora "tarefas vão para o quadro" na memória desta pasta e varredura de
memórias que mandem tarefa para outro destino), em silêncio quando nada mudou.

### Step 0b — Recorrentes que chegaram
`ArtifactData list recorrentes` (com `out_dir: <scratchpad>/rec`) e `get indice/ativos` (`out_dir`), depois
`python3 <skills>/tarefas/recorrentes.py --dir <scratchpad>/rec --indice <indice.json> --saida <scratchpad>/rec-plano.json`.
Para cada item: `criar` → conferir com `get` que `tasks/<id>` está livre e `set` do card (`criado_em`/`atualizado_em`
e o `em` do histórico = agora); `anotar` → linha no `historico` do card aberto. Nos dois, `update recorrentes/<rid>`
`{ultima: <ocorrencia>}` e o índice, num `batch` só. Sem coleção `recorrentes` → pular calado. Os cards gerados entram no
briefing e no Step 4 como qualquer tarefa (prazo hoje = "vence hoje"); recorrente com card aberto há mais de uma
ocorrência sobe em ⚠️ ("<título> está atrasada desde DD/MM").

### Step 1 — Coletar (em paralelo, só leitura, só as fontes do escopo)
Fazer as chamadas independentes na mesma rodada.

0. **Quadro primeiro:** do `indice/ativos`, as tarefas com `s` em `fazendo`, `esperando`, `a_fazer` e `entrada`; ler
   inteiras (`ArtifactData query tasks` com `["status","in",[…]]`) só as que estão em Fazendo/Esperando, com prazo
   até hoje+3, paradas há `parada_dias`+, ou citadas no `foco_amanha`. A **Entrada** (cards criados sozinhos nas
   conversas de ontem) é triada no briefing: uma linha por card, com a sugestão de coluna.
1. **Fontes do escopo** (as do texto de fontes, ou o padrão genérico). Elas servem para achar o que **ainda não está
   no quadro** (comparar pelas `chaves`: `linear:`, `jira:`, `notion:`, `conversa:`, `pr:`, `gcal:`…) e o que mudou nelas.
   O gestor de tarefas: todos os itens abertos atribuídos à pessoa, pela receita do tipo (paginar até o fim).
2. **Conversas** e **rotinas** desta conta (regra geral abaixo), sempre.

**Regra geral**
- **Conversas:** `list_sessions` (limit 30) só lista as conversas desta conta, e isso já é o filtro de escopo (não
  filtrar por pasta). Se aparecer uma conversa claramente de outro escopo do usuário, deixá-la de fora e citar numa
  linha. Considerar as não arquivadas com atividade nas últimas 72h. Das execuções de uma mesma rotina agendada,
  pegar só a mais recente. Para cada conversa relevante, `list_events` com limit 3–5 e ler só a ÚLTIMA mensagem do
  assistente: o que ficou pronto e o que ele pediu ao usuário. **Nunca supor o estado pelo título.**
- **Rotinas:** `list_scheduled_tasks`. Para cada uma do escopo, `list_task_runs` recente: apontar execução que
  falhou ou que deixou alerta.

Se alguma fonte falhar (MCP desconectado, auth), dizer qual em uma linha no fim do briefing e seguir com o resto.
Nunca travar o briefing inteiro por uma fonte.

### Step 1b — Gestor → quadro (só no quadro; gestor configurado e não pendente)
Montar tudo antes de gravar, em duas passadas, e gravar num `batch` só.

**Passada 1 — cards.** Para cada item aberto do gestor (fora dos prefixos de `legado`), procurar no índice a chave
`<prefixo_chave>:<ID>`:
- **Já tem card** → `update` só no que mudou: `prazo`, `links` (URL do item), `fonte`; coluna só **avança** pelo status
  do gestor (`entrada` → `a_fazer` → `fazendo`/`esperando`), nunca volta o que o quadro já andou e nunca vai para
  `feito` (fechar é do `/boa-noite`). O título do card fica (a pessoa pode ter encurtado). Linha no `historico` só se
  a coluna mudou (`por: "bom-dia"`).
- **Sem card com a chave** → procurar análogo entre **todos** os cards abertos sem chave do gestor (com chave de
  `legado`, manuais, de conversa), pelas regras da skill `tarefas` § 1.4: chave antiga citada no item, mesmo título, ou
  mesmo objetivo no mesmo projeto (só o projeto em comum não basta).
  - Achado claro → acrescentar a chave, o link e a `fonte` nesse card (linha no `historico`).
  - Dúvida (dois candidatos, ou parecido sem certeza) → **não criar**: no briefing, "ABC-123 é o card *X*? (ligo /
    card novo)"; grava depois da resposta; sem resposta, volta na próxima rodada.
  - Nada → `set` de card novo: título do item, coluna pelo status (`mapa_status` ao contrário; o que faltar, pela
    receita), `chaves: ["<prefixo_chave>:<ID>"]`, `fonte: {tipo, ref: <ID>}`, `links: [{rotulo: "<ID>", url}]`,
    `prazo`, `projeto`/tags pelo projeto do item quando bater com `tags_conhecidas`. Id = o ID do item (`ABC-123`) se
    estiver livre.

**Passada 2 — pais.** Com os cards da passada 1 (novos e existentes), para cada item que tem pai no gestor e cujo pai
tem card (achado pela chave): card filho sem `pai` → `pai` = card do pai. Card filho com outro `pai` → manter (a pessoa
organizou) e não mexer. Pai do gestor sem card no quadro (não é da pessoa) → nada.

- Um `batch` com as duas passadas (tarefas + `update` no índice). Primeira sincronização com mais de ~20 itens novos → dizer quantos
  e pedir um ok antes ("trago os N?"); quem não quer item velho no quadro fecha ele no gestor (`/boa-noite faxina`).
- Card aberto com chave do gestor que não veio na lista → `get` do item: fechado, cancelado ou com outra pessoa →
  "pode fechar hoje à noite" no briefing.
- No briefing, só os itens relevantes (mudaram nos últimos 30 dias, prazo em até 7 dias, ou em Fazendo/Esperando);
  os parados entram no quadro sem aparecer.

### Step 2 — Cruzar antes de mostrar
- Um pedido de conversa que também está noutra fonte de pendências (ex.: uma pauta) aparece uma vez só.
- Uma tarefa que tem evidência de feita (PR mergeada, conversa concluída) vai para "pode fechar hoje à noite", não
  para "a fazer".
- Duas conversas mexendo no mesmo PR ou branch vão para ⚠️ Alertas.
- **Estimativa não vira ⚠️ sem conferência.** Um número estimado (saldo, gasto, prazo calculado) só sobe como alerta
  depois de checar a fonte real; as fontes do escopo dizem onde conferir os casos conhecidos. Se não der pra
  conferir, escrever "estimado, não conferido" em vez de ⚠️.
- **Reunião ↔ tarefas:** para cada reunião de hoje, procurar no índice tarefas com tag `pessoa:<nome>` de quem
  participa (primeiro nome, sem acento), `projeto:`/`tema:` que apareçam no título, ou chave `gcal:<eventId>`.
  Ligadas → aparecem juntas no briefing ("15h com a Ana → *Proposta do fornecedor* segue em A fazer") e vão em
  `reunioes[].tarefas` no Step 4.
- **Fora do quadro:** item de outra fonte externa, PR ou conversa ativa sem tarefa correspondente (nenhuma chave bate;
  os itens do gestor já entraram no Step 1b)
  entra numa linha "Fora do quadro: N" com a sugestão de registrar; registrar só com o ok (skill `tarefas`, que
  procura análogo antes).
- **Preparo de reunião** (só nas que não são recorrentes de rotina, tipo daily): uma linha com quem é, o que ficou da
  última conversa com essa pessoa ou grupo (transcrição anterior na fonte de reuniões do escopo; tarefas e itens das
  fontes que citam o nome) e o que o usuário precisa levar ou decidir.
- Mais cruzamentos: os que as fontes do escopo definirem.

### Step 3 — Briefing (~1 tela)
**Seções extras e formato do escopo: os que as fontes definirem.** Sem formato nas fontes, este:
```
☀️ Bom dia (<escopo>[ · <Projeto>]) — <dia da semana>, DD/MM

⚠️ <só se houver: prod/segurança/dinheiro/conflito entre conversas>

Agenda: <HHh Reunião — preparo em 1 linha · HHh Reunião>  (ou "sem reuniões"; com recorte, só as de P)
Fora de <P>: <HHh · HHh>  (só no recorte "P + agenda resumida")
Foco sugerido: <1 item>
Decisões que destravam (máx. 3):
- [ ] <decisão curta> — <de onde vem>
Em andamento: <até 4 itens: o que é — status>
Entrada: <1 linha por card, com a coluna sugerida>
Gestor: N novos no quadro · N atualizados  (só se houver)
Fora do quadro: N — <quais, curto>
Conversas: tabela Conversa | Situação (1 frase) | Precisa de você?  (só as que têm algo novo)

(fontes que falharam: ...)
```

Regras de redação: idioma de `config/preferencias.idioma`, direto, sem jargão de git. **Prioridades, decisões e
tarefas do dia são checkbox (`- [ ]`), nunca lista numerada**: o usuário marca o que vai fazer, sem ordem imposta.
Cada item diz *o que é · em que pé está · próximo passo*. No máximo 3 decisões. Linkar as conversas como
`[título](#<sessionId>)`.

### Step 4 — Foco e registro
Perguntar com **um** AskUserQuestion com as tarefas pendentes (Fazendo, A fazer, Esperando e o que o briefing trouxe)
**em ordem de prioridade**: até 4 perguntas, todas `multiSelect: true`, até 4 opções cada (pedido de 14/10).

- **Ordem:** a 1ª pergunta tem as mais prioritárias, a 4ª as menos. Prioridade = atrasada ou vence hoje > ligada a
  reunião de hoje > `prioridade: alta` > em Fazendo > prazo mais perto > `foco_amanha` do último fechamento > dias
  parada. Não há rótulo de "hoje"/"semana": o header é só a faixa (`Prioridade 1`… `Prioridade 4`, ou o tema comum
  quando a pergunta inteira é de um assunto só).
- **Agrupar o que anda junto** numa opção só, para caber mais: mesmo projeto e mesma pessoa/tema e mesma próxima ação
  (ex.: as 3 aulas do curso → `Aulas do curso (3)`; recados soltos → `Responder recados (5)`). A
  `description` lista os itens. Marcar a opção = todos os cards do grupo entram no plano.
- **Texto da pergunta:** `O que entra hoje? Use "Outro" para comentar alguma tarefa ou acrescentar outras.`
- Mais pendências do que cabe: a última pergunta diz quantas ficaram de fora ("mais 7 no quadro"); o usuário puxa
  qualquer uma pelo "Outro", ou roda o `/bom-dia` de novo.
- `label` curto (até ~5 palavras, nome que o usuário reconhece); `description` = coluna · prazo · próximo passo.
- O que vier no "Outro": comentário sobre uma tarefa → linha no `historico` dela (`por: "bom-dia"`); tarefa nova →
  card pela skill `tarefas` (procurando análogo antes), já no `plano` do dia.

**Rodar de novo no mesmo dia** (ele pode chamar `/bom-dia` mais de uma vez): ler `dias/<hoje>.bom_dia` primeiro. O
briefing vira só o que mudou desde o `gerado_em` anterior (conversas, reuniões que ainda vêm, cards fechados pelo
`fechar`); as perguntas mostram só o que **ainda não está no plano** e não foi fechado; as escolhas novas são
**acrescentadas** ao `plano` (nunca substituir, nunca desmarcar o que já está), e `gerado_em` vira uma lista de rodadas.
O mesmo vale para `reunioes`, `foco` e `destravar`: unir com o que já está, nunca trocar (ver § Recorte por pasta → Diário).

Depois:
- Gravar `dias/<hoje>` no quadro (`set` se não existe; `update` com `if_version` se já existe, sem apagar um
  `boa_noite` que esteja lá) com `bom_dia`: `gerado_em`, `plano` (os itens marcados, cada um com `tarefa: <id>`
  quando houver, `feito: false`, e `chip: <task_id>` depois do Step 5), `reunioes` (hora, título, `tarefas` ligadas, nota de preparo), `foco` (ids) e
  `destravar` (decisões). A página do quadro mostra isso no topo e o usuário marca os itens por lá.
- Item marcado que **não tem tarefa** → criar no quadro (skill `tarefas`, `status: a_fazer`, com tags de
  projeto/pessoa) e pôr o id no `plano`. Tarefa escolhida que estava em `a_fazer`/`entrada` → mover para `fazendo`
  (linha no histórico, `por: "bom-dia"`).
- Triagem da Entrada: o que o usuário confirmar muda de coluna/projeto/tags; o que ele disser que não é tarefa sai
  (`delete` + índice `s: "apagada"`).
- Ferramentas externas (gestor de tarefas, pauta…): criar ou mudar item lá só quando o usuário pedir aquela escrita;
  no gestor, pela receita do tipo, com as `regras` do `config/gestor`, e só se o modo daquela operação permitir
  (`escrever.criar` para criar, `escrever.editar` para editar; `nunca` → dizer que está desligado). A chave criada vai
  para o card.

### Step 5 — Dar partida nas tarefas do dia (obrigatório, decidido em 14/10)
O bom-dia não termina no briefing nem na pergunta: **todo item marcado no Step 4 sai daqui encaminhado**, sem
perguntar "quer que eu abra?" e sem pular nenhum. Um encaminhamento por item (um grupo do Step 4 = um só). Antes, ver
no card (`conversas`) e nas conversas do Step 1 se a tarefa já tem **conversa aberta** (não arquivada, não fechada
pelo `fechar`) sobre ela:

- **Tem conversa aberta** → é ela que segue: `mcp__ccd_session_mgmt__send_message` nela com um recado curto (contexto
  do dia, o que entra hoje, o próximo passo do card) e o link para o usuário entrar. **Não abrir chip.** "undelivered"
  → ela pega o recado quando for aberta; dizer isso e dar o link.
- **Coisa rápida que cabe aqui** (responder, conferir, uma consulta) → fazer nesta conversa, com o ok antes de mandar
  mensagem ou gravar.
- **Nenhuma conversa aberta** → **tarefa sugerida** (`mcp__ccd_session__spawn_task`, o chip que o usuário clica):
  - `title`: nome curto (abaixo, § Nomes curtos); `tldr`: o que a conversa vai fazer hoje;
  - `prompt` autossuficiente (objetivo do dia, contexto, arquivos, links, próximo passo, e as conversas arquivadas
    do card como referência), terminando com:
    ```
    Card do quadro: <id> ("<título>")
    Tarefa do dia: dias/<AAAA-MM-DD>
    Esta conversa passa a ser a conversa original desta tarefa: o usuário fala com ela, e é ela que decide e
    orquestra. Se precisar abrir outras conversas para executar partes, elas reportam aqui (send_message) e
    não pedem decisão ao usuário por lá.
    ```

Gravar o `task_id` de cada chip no item do `plano` (`chip`; recado numa conversa → `conversa: <id>`), e no card uma linha de `historico` (`por: "bom-dia"`,
"tarefa sugerida: <title>"). Rodar de novo no mesmo dia → não abrir chip de novo para item que já tem `chip`.

**Um chip por processo, não por projeto:** itens do mesmo processo (mesma linha de trabalho, mesmo código) podem ir
juntos num chip; processos diferentes do mesmo projeto ganham um chip cada.

**Nomes curtos** (pedido de 20/10; vale para chips, conversas e cards novos): **1 a 3 palavras**, o assunto do jeito
que o usuário chama. Sem o nome do projeto (a pasta e o quadro já dizem qual é), sem data, sem emoji, sem `·`, sem
verbo genérico. Ex.: `Dash de atividade`, `Fluxo comercial`, `Telas produção`. ❌ `Site · trabalho 20/10`,
`App · dash de atividade dos clientes`.

No fim, uma linha por item: feito aqui · recado em [conversa](#id) · `chip "<title>"`.
Se `spawn_task` falhar, dizer qual item ficou sem chip e por quê; nunca omitir em silêncio.

## Anti-patterns
- ❌ Misturar escopos: mostrar outro escopo nesta conta, consultar fonte de outro escopo, ou escrever no quadro/diário
  de outro escopo.
- ❌ Gravar o plano do dia num diário `.md` legado quando o quadro responde (o diário é `dias/` no quadro).
- ❌ Decidir o escopo pelo nome do app, por `CLAUDE_CONFIG_DIR`, ou pelo título/pasta da conversa. A pasta só sugere
  o recorte por projeto, e só depois da resposta (§ Recorte por pasta).
- ❌ Restringir a um projeto sem perguntar, ou perguntar numa pasta raiz.
- ❌ Escrever no git, mudar status de item em ferramenta externa, ou mover tarefa do quadro para `feito`. Fechar é
  trabalho do `/boa-noite`. Criar item externo só quando o usuário pedir aquela criação; nunca por conta própria.
- ❌ Deixar item aberto do gestor fora do quadro, ou duplicar card que já tem a chave dele.
- ❌ Ler ou sincronizar ferramenta marcada como `legado`.
- ❌ Terminar sem encaminhar as tarefas do dia (Step 5), ou abrir chip para tarefa que já tem conversa aberta.
- ❌ Despejar lista crua (dezenas de issues, `git status`, todas as tarefas). Filtrar e traduzir.
- ❌ Inventar o estado de uma conversa sem ler o fim dela.
- ❌ Gravar segredo, token ou senha em `config/fontes`, `config/gestor` ou em qualquer documento do quadro.

## Melhoria contínua
Aprendeu algo sobre o fluxo do usuário?
- Preferência de formato ou de jeito de trabalhar → `config/preferencias` (campo certo ou `notas` com data), avisando
  em uma linha.
- Fonte nova, ID, regra ou seção do escopo → atualizar o texto das fontes onde ele mora (`config/fontes` com o ok do
  usuário, ou o arquivo local `~/.claude/tarefas/fontes-<escopo>.md` se é de lá que veio). Nunca nesta skill.
- Mudança de processo que vale para todo mundo → este SKILL.md.

# Migrações do quadro

Lido só quando `config/schema.versao` é menor que a atual (4) ou o quadro tem restos de versões antigas. Quadro novo
nasce na versão atual e nunca passa por aqui.

**Quando:** na primeira escrita da rodada que achar a versão antiga (`ACHAR-QUADRO.md` § Busca completa, passo 6), em
ordem (v1 → v2 → v3 → v4), cada uma num `batch` com `if_version`. No fim de cada uma, `config/schema` com a `versao`
nova e `"v<N> em AAAA-MM-DD"` acrescentado em `migracoes`. Dizer em uma linha que o quadro foi atualizado.

## Quadro sem `formato`
`update` em `config/schema` com `formato: "quadro-tarefas"`. Quadro sem `formato` é reconhecido por `versao` + `escopo`.

## v1 → v2: `config/gestor`
Se `config/preferencias.export.destino` é `linear`, `jira` ou `notion` (qualquer caixa) e ainda não há `config/gestor`,
semear `config/gestor` com `tipo` = destino (minúsculo), `nome` = destino, `prefixo_chave` = `tipo`, `mapa_status` =
`export.mapa_status`, `config: {}`, `escrever: {criar: "sob_pedido", editar: "propor_no_boa_noite"}` (o comportamento
da v1: só fechar item terminado), `regras: []`, `legado: []`, **`pendente: true`** (falta o `config` obrigatório:
nada de sincronizar nem escrever até o setup descobrir e a pessoa confirmar). Sem `export.destino`: só sobe a versão
(falta de `config/gestor` = `nenhum`). `export` é obsoleto: fica onde está, lido só como reserva por quadro sem
`config/gestor`; ninguém escreve mais nele.

## v2 → v3: card em vários projetos + `config/projetos`
Para cada card com mais de uma tag `projeto:` e sem `projetos`, gravar `projetos` = `[projeto, …os outros]` (nome de
cada slug = o `projeto` de outro card com esse slug; sem nenhum, o slug com hífen virando espaço e cada palavra com
maiúscula) e o `ps` no índice. Os demais cards ficam: ausência de `projetos` vale `[projeto]`. `config/projetos` não é
semeado (nasce quando a pessoa cadastra uma pasta).

## v3 → v4: preferências explícitas e `config/fontes` estruturado
A v4 tira das skills o que era o jeito de uma pessoa e põe em `config/preferencias`. Para o quadro migrado **continuar
funcionando igual**, a migração grava o comportamento que a v3 tinha fixo (campos que já existirem não são tocados):
- `config/preferencias`:
  - `locale` = `idioma`, exceto `en` → `en-GB`: a página da v3 lia e mostrava datas sempre como dia/mês, e `en-US`
    trocaria o sentido de `^10/11` nos atalhos. Dizer em uma linha que dá para mudar para `en-US`. `fuso` = o do sistema (`sh <skills>/tarefas/py <skills>/tarefas/sistema.py` → `fuso`; sem ele,
    não gravar: a página e os scripts usam o do sistema); `area_padrao` = o id da primeira área (era o que a página
    usava). `semana_inicia` = `1` (a página da v3 mostrava a semana de segunda a domingo, em qualquer idioma).
  - `titulo_conversa` = `{automatico: true, max: 25, manter: []}`: a v3 dava nome curto à conversa nova a não ser que
    o campo dissesse `false`; a v4 só dá com `true`. Se o campo já existe, só acrescentar o que faltar (`automatico`
    ausente → `true`).
  - `automacao` = `{encaminhar_plano: "chips", renomear_conversas: true, arquivar_conversas: "propor",
    ancora_memoria: true, linha_claude_md: true}`.
  - `codigo` = `{usa_git: true, remoto: "origin", branch_base: null, ruido: [".claude/skills", ".gemini/skills",
    "AGENTS.md", "GEMINI.md", "CLAUDE.md"], copiar_fora_do_git: true}` (a lista de ruído era a fixa do `fechar` na v3).
  - `resumo` = `{modelo: "haiku", confirmar_acima: 15}`.
  - `regras_fechamento`: acrescentar, se não houver equivalente, as duas regras que a v3 tinha fixas no `/boa-noite`:
    "Conversa que terminou esperando o usuário e ele não voltou = encerrada" e "Tarefa com data que passou há semanas
    sem registro: presumir que aconteceu e propor fechar".
  - `agendas` (se houver) passa para `config/fontes.agenda.calendarios` e sai daqui.
  - `fontes.repos` (se houver; a v3 guardava aqui os padrões de pasta de código) sai daqui e vira raiz, abaixo.
- `config/projetos`: sem `raizes` (ou sem o documento), gravar `raizes` = as raízes padrão da v3: a home, a pasta
  `Github` da home se existir, e a pasta-mãe de cada padrão de `preferencias.fontes.repos` (`~/code/Projetos/**` →
  `~/code/Projetos`), em caminho absoluto, só as que existem. Sem isso, o `/bom-dia` passaria a perguntar "só este
  projeto?" em pastas onde a v3 nunca perguntava. `itens` fica como está (ou `{}`).
- `config/fontes`:
  - `{versao: 1, texto}` → `{versao: 2, texto}` com o mesmo `texto`, mais `agenda.calendarios` (das `agendas` acima) e
    `conversas.backend` (`app` no app desktop, senão `transcritos`). Com um conector de reuniões ligado na sessão,
    `reunioes.conector` = ele (a v3 lia o Granola por padrão quando estava ligado), a não ser que o `texto` descreva
    outra fonte de reuniões: aí vale o `texto` e `reunioes` fica ausente (perguntar na próxima `/quadro-tarefas fontes`). Os demais campos ficam ausentes:
    o `texto` continua valendo para o que ele descreve.
  - Sem `config/fontes` e com o arquivo local legado `fontes-<escopo>.md` → `texto` = o conteúdo dele (é da própria
    pessoa; dizer em uma linha que foi para o quadro). Procurar em `<dados>/tarefas/` e, se não houver, na pasta de
    antes da v0.3 (`caminhos.py --tudo` → `legado`, `<legado>/tarefas/`), como já fazem o `quadros.py` e o hook. O
    arquivo fica onde está.
- Chaves `gcal:<eventId>` não são reescritas: valem como `agenda:<eventId>`.
- **Página:** a página publicada na v3 é a antiga (só português, sem fuso, sem conversas do CLI). Remontar e publicar
  na mesma URL (`quadro-tarefas` § Atualizar a página) e gravar `config/schema.pagina`. Se `config/preferencias.tema`
  existe com um valor diferente de `padrao` (tema embutido por nome, de antes do `config/tema`) e não há `config/tema`,
  não remontar ainda: dizer em uma linha que o tema antigo não vem no plugin e oferecer o `quadro-tarefas` § Tema (o
  site da marca, um guia, ou o CSS antigo, se a pessoa o tiver). Sem resposta, migrar o banco e manter a página
  publicada. `preferencias.tema` sai quando o `config/tema` for gravado. Sem a tool `Artifact` nesta
  sessão, migrar o banco mesmo assim e dizer em uma linha que a página se atualiza no próximo `/quadro-tarefas`.

## Restos de versões antigas
- **`DIARIO-*.md`:** diários em arquivo, de antes do `dias/` no quadro. Se o quadro estiver inacessível e as fontes
  disserem onde há um, ler; nunca gravar nele quando o quadro responde.
- **`<dados>/tarefas/fontes-<escopo>.md`** (ou em `<legado>/tarefas/`): fontes em arquivo local. Lido só por quadro sem `config/fontes` (e migrado
  na v3 → v4).
- **`config/preferencias.export`:** ver v1 → v2.

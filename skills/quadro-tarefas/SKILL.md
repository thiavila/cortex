---
name: quadro-tarefas
description: >
  Abre o quadro de tarefas do usuário (quadro em artefato com banco) no navegador; se ele ainda não existe
  nesta conta, cria: descobre as ferramentas ligadas (agenda, reuniões, chat, código, gestor de tarefas), o
  idioma, o fuso e o sistema, confirma em uma ou duas perguntas, publica a página, grava preferências, fontes,
  gestor, schema e índice, importa um pacote da tarefas-io se houver, e lembra o link no atalho local. Use quando
  pedirem "abre meu quadro", "quadro tarefas", "abre o quadro", "cria meu quadro de tarefas", "configura o
  quadro pra mim", "configura meu gestor de tarefas no quadro", quando a skill tarefas disser que esta conta não
  tem quadro, ou para recriar o quadro na conta certa (English: "open my board", "set up my task board",
  "connect my Asana/Linear/Jira to the board"). Também procura instruções antigas que mandam gerir tarefas em
  outro lugar e propõe juntar tudo no quadro ("varrer fontes"), e veste o quadro com a marca da pessoa ou da
  empresa dela ("muda o tema do quadro", "coloca o quadro com a cara da minha empresa").
user_invocable: true
argument-hint: "(nenhum) | importar <pacote quadro-tarefas-*.json> | gestor (configurar o gestor de tarefas) | fontes (rever as ferramentas) | varrer (procurar instruções conflitantes) | tema [<site ou arquivo da marca>]"
---

# quadro-tarefas — abrir ou criar o quadro

`<skills>` = a pasta-mãe do Base directory desta skill (vale numa pasta de skills e dentro do plugin).
Scripts: `sh <skills>/tarefas/py <script>`. `<dados>` = `sh <skills>/tarefas/py <skills>/tarefas/caminhos.py`.

Arquivos: `<skills>/tarefas/app/` (`board-src.html`, `style-base.css`, `build.py`),
contrato em `<skills>/tarefas/SCHEMA.md`, como achar o quadro em `<skills>/tarefas/ACHAR-QUADRO.md` (o § 0 lista as
ferramentas que só existem no app desktop e o que fazer sem elas).
Pacotes de import/export (gerados pela `tarefas-io`): `<dados>/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json`.

**Idioma:** perguntar e responder no idioma da pessoa (o jeito que ela escreve); depois de criado, o de
`config/preferencias.idioma`. As perguntas abaixo estão em português: traduzir.

## 1. Já existe? Então só abre
1. Seguir `ACHAR-QUADRO.md` § Busca completa (lista de artefatos da conta).
   - **Achou:** o quadro existe nesta conta. Abrir no navegador (chamar `/quadro-tarefas` já é o pedido de abrir), como
     em `ACHAR-QUADRO.md` § 0. Responder com o link e uma linha de estado (do `indice/ativos`: N abertas, N na
     Entrada). `config/schema.versao` abaixo de 4 → as migrações (`MIGRACOES.md`) antes, inclusive a remontagem da
     página (§ Atualizar a página).
     Página publicada por uma versão mais antiga do plugin (`config/schema.pagina` ausente ou menor que a `version` do
     `.claude-plugin/plugin.json` do plugin) → § Atualizar a página, dizendo em uma linha o que mudou. Sem `config/gestor` ou com ele
     pendente → uma linha oferecendo configurar ou completar (§ Gestor). Fim. Não recriar.
   - **Argumento `gestor`:** achou o quadro → só o § Gestor (reconfigurar o que a pessoa pedir).
   - **Argumento `fontes`:** achou o quadro → só os passos 2–4 do § 2 para `config/fontes` (e `config/projetos`),
     mostrando o que está gravado e o que mudou nos conectores; gravar com `update` + `if_version` depois do ok.
   - **Argumento `varrer`:** achou o quadro → só o § Varredura.
   - **Argumento `tema`** (ou pedido de mudar o visual): achou o quadro → só o § Tema.
   - **Não achou:** seguir para criar. Um quadro de outra conta (que não responde aqui) não conta: o desta conta
     é criado do zero ou a partir de um pacote exportado do outro.

## 2. Não existe: cria
Princípio: **descobrir primeiro, perguntar pouco.** Tudo o que dá para ler (sistema, conectores, quem a pessoa é em
cada ferramenta, git) é lido antes; a pessoa só confirma, em uma ou duas rodadas de perguntas.

1. **Capacidades** (`ACHAR-QUADRO.md` § 0): sem `Artifact`/`ArtifactData`, parar e dizer por quê. Anotar quais
   ferramentas do app existem (elas decidem os padrões de automação abaixo).
2. **Pacote.** Se o usuário passou um, usar. Se existe algum `quadro-tarefas-*.json` em `<dados>/tarefas-exports/`
   (ou em `~/.claude/tarefas-exports/`), oferecer importar o mais recente que pareça deste quadro (pelo
   `escopo`/`nome` das preferências do pacote). Com pacote, as preferências dele valem como padrão, mas
   `config/fontes`, `config/gestor` e `config/projetos` são **reconfirmados** (pode ser outra máquina ou empresa).
3. **Descobrir** (só leitura, em paralelo, sem comentar cada passo):
   - **Sistema:** `sh <skills>/tarefas/py <skills>/tarefas/sistema.py` → `so`, `fuso`, `locale`, `app_desktop`, `git`.
     Sem Python → seguir sem os scripts (idioma e fuso perguntados) e dizer o que instalar.
   - **Idioma e formato:** `idioma` pelo jeito que a pessoa escreve (`pt-BR`, `en`, `es`…); `locale` = o do sistema
     se for do mesmo idioma, senão o mais comum dele (`en` → `en-US`); `fuso` = o do sistema (IANA);
     `semana_inicia` pelo costume do `locale` (domingo nos EUA e no Brasil, segunda na maior parte da Europa).
   - **Conectores ligados:** passar pelas tools da sessão (as adiadas também: `ToolSearch` por palavras como
     `calendar`, `meeting`, `transcript`, `notes`, `slack`, `teams`, `mail`, `github`, `gitlab`, `issues`, `tasks`,
     `project`) e classificar cada serviço por papel: **agenda**, **reuniões** (gravador ou notas de reunião), **chat**,
     **e-mail**, **código**, **gestor de tarefas** (Linear, Jira, Notion, Asana, ClickUp, GitHub Issues, Azure DevOps,
     Trello, Todoist, Monday…). Para cada um, uma chamada "me"/"whoami"/"current user" (só leitura) → `eu`; na
     agenda, a lista de calendários (o principal da pessoa como padrão). Conector que falha ou pede login fica de
     fora (citar no fim).
   - **Código:** com `git` no sistema, a pasta atual é um repositório? (`git -C <cwd> rev-parse --show-toplevel`,
     remoto e branch padrão). Pasta-mãe com vários repositórios → candidata a raiz em `config/projetos.raizes`.
   - **Conversas:** `app` se a tool `get_session` existe nesta sessão (app desktop), senão `transcritos`.
4. **Confirmar** — rodada 1, um `AskUserQuestion` com até 4 perguntas (sem a tool: em texto, numerado), cada uma com o
   que foi descoberto como primeira opção "(Recomendado)":
   1. **O quadro:** `"<Nome sugerido>" · <idioma> · <data de exemplo no locale> · <fuso>` (nome: `Trabalho` com
      contexto de empresa, senão `Pessoal`, no idioma); no "Outro", nome, áreas e correções.
   2. **Ferramentas** (`multiSelect`): uma opção por papel achado (`Agenda: <serviço> (<calendário>)`, `Reuniões:
      <serviço>`, `Chat: <serviço>`, `Código: git + <host>`…). O que for desmarcado não entra em `config/fontes`.
   3. **Gestor de tarefas:** os achados que gerem tarefas (um por opção) e `Não uso`. Os detalhes vêm no § Gestor.
   4. **Como o Claude trabalha com o quadro** (`multiSelect`, já marcado o que é padrão):
      `Card automático por conversa, avisando` (desmarcado = perguntar antes de criar o card) ·
      `Abrir conversas para o plano do dia` (só se houver `spawn_task`; marcado = `encaminhar_plano: "chips"`, senão
      `perguntar`) · `Dar nomes curtos e arquivar conversas que terminaram` (só se houver `set_session_title` /
      `archive_session`) · `Lembrar do quadro na memória e no CLAUDE.md`.
   Rodada 2, só se precisar, numa pergunta: o § Gestor (passos 2–3) e o tema (§ Tema, passo 1). Nada mais é perguntado:
   o resto fica no padrão de `SCHEMA.md` § `config/preferencias` e pode ser mudado depois em qualquer conversa.
5. **Montar a página:** `sh <skills>/tarefas/py <skills>/tarefas/app/build.py --titulo "Cortex · <Nome>" --out <scratchpad>/board-<escopo>.html`
   (o script checa o JS quando há Node). Com tema da marca, antes o § Tema passos 2 a 4 e `--tema-arquivo
   <scratchpad>/tema-<escopo>.css` (e `--fontes "<url>"` se houver); sem fontes de fora, `--sem-fontes-externas`.
   **Tema efetivo** (um só, nesta ordem): o que a pessoa escolheu (marca nova ou neutro) → sem escolha e com pacote
   que traga `config/tema`, o do pacote → neutro. `<escopo>` = slug do nome (ou o do pacote). Nada da pessoa vai no
   HTML: a página lê de `config/preferencias`.
6. **Publicar** pelas regras da tool Artifact (quickstart `other` na primeira vez; publish com
   `capabilities: {"db": {}, "user": {}}`, `icon: "checklist"`, `description` de uma frase). O artefato pertence à
   conta desta sessão, e é por isso que só ela o acha depois.
7. **Semear o banco** (`batch`), tudo no formato de `SCHEMA.md`:
   - `config/preferencias`: `escopo`, `nome`, `sub`, `areas` (padrão: uma, `geral` com o nome no idioma),
     `area_padrao`, `idioma`, `locale`, `fuso`, `semana_inicia`, `dias_uteis` e `horario` (padrão seg–sex, 9–18),
     `card_por_conversa` (`ignorar_titulos: []`), `titulo_conversa`, `fechar`, `automacao`, `codigo` e `resumo`
     pelas respostas da pergunta 4 e da descoberta (sem a tool correspondente, a automação fica desligada),
     `parada_dias: 14`, `zumbi_dias: 60`, `arquivar_feitas_dias: 60`, `regras_fechamento: []`, `notas: []`.
   - `config/fontes` `{versao: 2, …}` com os papéis confirmados (cada um com `conector` e `eu`), `conversas.backend`,
     `texto: ""`.
   - `config/projetos` se houver raiz ou pasta de projeto confirmada (`raizes`, e o repositório atual como projeto se a
     pessoa quiser).
   - `config/gestor` (§ Gestor; `{tipo: "nenhum"}` se a pessoa não usa; `pendente: true` se os detalhes ficaram para
     depois).
   - `config/schema` `{formato: "quadro-tarefas", versao: 4, pagina: <version do plugin.json>, escopo, criado_em, migracoes: []}`,
     `indice/ativos` `{itens: {}, atualizado_em}` e `config/tema` com o tema efetivo, se ele não for o neutro (§ Tema,
     passo 6), ou `{fontes_externas: false}` se for o caso.
   Com pacote e `--com-config`, os documentos do pacote entram no passo 8 e depois **tudo o que a pessoa confirmou no
   passo 4 é regravado por cima**: `config/fontes`, `config/gestor`, `config/projetos` e, em `config/preferencias`,
   os campos confirmados ou descobertos nesta criação (nome, áreas, `idioma`, `locale`, `fuso`, `semana_inicia`,
   `card_por_conversa`, `titulo_conversa`, `fechar`, `automacao`, `codigo`). Do pacote ficam só os campos que ninguém
   confirmou aqui (`tags_conhecidas`, `regras_fechamento`, `notas`, prazos…).
8. **Importar** o pacote seguindo a `tarefas-io` § Import (prévia → ok → gravar). Depois do import com `--com-config`:
   conferir que `config/schema` tem `formato`, a `versao` atual (senão `MIGRACOES.md`) e `pagina`; tirar `principal`
   das preferências importadas (o desempate é decidido nesta conta); regravar as escolhas confirmadas (passo 7) e
   `config/tema` com o tema efetivo do passo 5 (ou apagá-lo, se o efetivo for o neutro), para o banco bater com a
   página publicada e com o que a pessoa acabou de escolher.
9. **Lembrar** no atalho local: `sh <skills>/tarefas/py <skills>/tarefas/quadros.py lembrar --url <url> --titulo "Cortex · <Nome>"`.
10. **Verificar as escolhas por quem usa** (uma linha cada, só o resultado): `get` de `config/preferencias`,
    `config/fontes` e `config/gestor` (gravados como esperado); gestor configurado → a leitura de abertos da receita
    uma vez (quantos itens); agenda → os eventos de hoje (quantos); conversas (backend `app` ou `transcritos`;
    `nenhum` → pular) → `conversas.py extrair --backend
    <backend> --sessao <id desta conversa> --saida <scratchpad>/conv-teste` (sem `--quadro` e sem `confirmar`: só para
    ver que funciona); `recorrentes.py` com uma pasta vazia (o Python roda). O que falhar → dizer o quê e como
    resolver, sem desfazer o quadro.
11. **Abrir** no navegador como no § 1 e responder com o link, quantas tarefas entraram e, se havia um quadro antigo,
    que ele pode ser apagado depois de conferido. Uma linha lembrando que o resto (dias úteis, regras de
    fechamento, modelo do resumo…) muda dizendo numa conversa.
12. **Varredura** (§ Varredura): o quadro acabou de nascer, então é a hora de juntar numa fonte só o que antes mandava
    gerir tarefas por outros caminhos.

## Tema — vestir o quadro com a marca da pessoa
O quadro nasce no tema neutro (`style-base.css`). Ele pode ganhar as cores, as fontes e o jeito da marca da
pessoa, em geral a da empresa dela. Nada de marca vem pronto no pacote: o tema é montado a partir do que a pessoa mostra.

1. **Quando oferecer e o que perguntar.** Na criação (§ 2, passo 4, na segunda rodada de perguntas). Se houver
   contexto de empresa (e-mail corporativo na agenda, conectores de trabalho ligados, nome de quadro como `Trabalho`,
   pasta de um repositório da empresa), oferecer assim: "Quer o quadro com a cara da sua empresa? Me manda o site (ou um guia
   de marca, PDF, print) e eu sigo as cores e fontes. Se não, fica no tema neutro." Sem contexto de empresa, oferecer
   do mesmo jeito, com "da sua marca" no lugar de "da sua empresa". A pessoa pode pular; não insistir.
   Com o argumento `tema` num quadro que já existe, pedir só a fonte (site ou arquivo), se não veio junto.
2. **Ler a marca.** Do site: buscar a página inicial (WebFetch, ou `curl -sL` para ver o HTML) e as folhas de estilo
   que ela carrega; procurar variáveis CSS (`--primary`, `--brand`…), as cores que mais se repetem em botões, links
   e cabeçalhos, `theme-color`, as famílias de `font-family` e o arredondamento dos botões. De um PDF, imagem ou
   print: ler as cores e o tipo de letra que aparecem. Se a ferramenta de navegador estiver ligada e o site precisar
   de JS para mostrar algo, tirar um print. Não baixar nem executar nada do site, só ler.
3. **Traduzir para os tokens do quadro.** Escrever `<scratchpad>/tema-<escopo>.css` só com sobrescrita de variáveis
   (as mesmas de `style-base.css`): `--bg`, `--surface`, `--surface-2`, `--line`, `--fg`, `--muted`, `--accent`,
   `--accent-soft`, `--on-accent`, `--info`, `--info-soft`, `--f-display`, `--f-body`, `--r` e, se fizer sentido,
   `--shadow`. Regras:
   - A cor principal da marca vai em `--accent`; `--accent-soft` é ela bem clara (no escuro, bem escura).
     `--warn`/`--bad` continuam os da base, a não ser que a marca use uma dessas cores como principal.
   - Contraste mínimo: `--fg` sobre `--bg` e `--surface` ≥ 7:1; `--muted` ≥ 4,5:1; `--on-accent` sobre `--accent` ≥ 4,5:1.
     Calcular (luminância relativa do WCAG) e ajustar o tom até passar; nunca publicar abaixo disso.
   - Escuro: repetir os tokens dentro de `@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) { … } }`
     e de `:root[data-theme="dark"] { … }`, com a marca adaptada ao fundo escuro. Se a marca for só clara (o site não
     tem modo escuro e a pessoa prefere assim), repetir os tokens claros nos dois blocos com `color-scheme: light`.
   - Fontes: com `fontes_externas: false` (a pessoa não quer nada carregado de fora), usar só fontes do sistema na
     lista (`--f-body: "Nome da Marca", system-ui, sans-serif`) e montar com `--sem-fontes-externas`. Senão, se a
     família da marca existir no Google Fonts, montar a URL `https://fonts.googleapis.com/css2?family=…&display=swap`
     para o `--fontes`. Fonte proprietária → a mais parecida do Google Fonts no lugar, com o nome original primeiro na
     lista (`--f-display: "Nome da Marca", "Parecida", sans-serif`) e dizer isso à pessoa.
   - Pode haver um ajuste leve de forma além dos tokens (ex.: títulos em caixa alta, raio das colunas), só com
     seletores que já existem no `board-src.html`. O `build.py` recusa `@import`, `url(` e tags: o artefato não carrega
     estilo de fora além do Google Fonts. Só valem `@media`, sem escapes (`\`), e funções de cor e conta
     (`rgb`, `hsl`, `oklch`, `color-mix`, `var`, `calc`, `clamp`, gradientes…).
4. **Montar e conferir.** `build.py` com `--tema-arquivo` (e `--fontes`). Abrir o HTML montado num navegador ou tirar
   um print headless (claro e escuro) e olhar antes de publicar: legível, cara da marca, nada quebrado.
5. **Publicar.** Na criação, segue o § 2. Num quadro que já existe: `Artifact read` da URL e depois publish do HTML
   novo **na mesma URL** (sem mudar `capabilities`); o banco e as tarefas ficam como estão.
6. **Gravar** `config/tema` (`set`, ou `update` com `if_version` se já existe; contrato em `SCHEMA.md` § `config/tema`):
   o CSS, a URL de fontes, `fontes_externas` e de onde veio, para o quadro poder ser remontado igual (nova versão do plugin, troca de tema).
   Mostrar o print à pessoa e dizer em uma linha o que foi seguido (ex.: "azul e fonte do site da empresa; a fonte do
   logo é paga, usei a Inter no lugar"). Para voltar ao neutro: montar sem `--tema-arquivo`, publicar na mesma URL e
   apagar `config/tema`.

## Atualizar a página (quadro que já existe)
Quando a página publicada é de uma versão mais antiga do plugin (ou numa migração): `get config/tema` → montar com o
`build.py` como no § 2 passo 5 (com `--tema-arquivo` do `css` gravado, `--fontes` ou `--sem-fontes-externas` conforme
o `config/tema`; sem ele, neutro) e o título atual do artefato → `Artifact read` da URL → publish do HTML novo **na
mesma URL**, sem mudar `capabilities` → `update config/schema` com `pagina` = a versão do plugin. O banco e as tarefas
ficam como estão.
**Trava do tema antigo:** se `config/preferencias.tema` existe com valor diferente de `padrao` (tema embutido por nome,
de antes do `config/tema`) e não há `config/tema`, não remontar: a página publicada é a única que ainda tem a marca.
Dizer em uma linha que o tema antigo não vem no plugin e oferecer o § Tema (o site da marca, um guia, ou o CSS antigo,
se a pessoa o tiver). Só remontar depois que o `config/tema` for gravado (e então tirar `preferencias.tema`) ou que a
pessoa disser para seguir com o tema neutro (então tirar `preferencias.tema`). Sem resposta, manter a página.

## Gestor — configurar `config/gestor`
Contrato em `SCHEMA.md` § `config/gestor`; receitas em `<skills>/tarefas/referencias/gestores/<tipo>.md`.
1. **Qual ferramenta:** sugerir pelos conectores ligados nesta sessão (Linear → `linear`; Atlassian/Jira → `jira`;
   Notion → `notion`; qualquer outro gestor de tarefas — Asana, ClickUp, GitHub Issues, Azure DevOps, Trello,
   Todoist, Monday… → `generico`; vários → perguntar qual é o de tarefas). Uma pergunta só. "Não uso" →
   `{tipo: "nenhum"}`. A ferramenta sem conector ligado → explicar que precisa ligá-lo (conectores do claude.ai ou
   `/mcp`) e gravar `pendente: true`.
2. **Detalhes pelo conector, sem perguntar o que dá para ler:** `linear`/`jira`/`notion` → o § `config` da receita
   (time/projeto/base, status existentes); `generico` → `gestores/generico.md` § Descobrir (monta a `receita`). Propor
   o `mapa_status` a partir dos status lidos, a `leitura` (padrão `atribuido_a_mim`) e o padrão
   `escrever: {criar: "propor_no_boa_noite", editar: "propor_no_boa_noite"}`.
3. **Perguntar numa mensagem:** confirma o mapa, o que entra no quadro (`leitura`) e o modo de escrita? Tem regra da
   casa (label obrigatória, o que nunca criar, padrão de título)? Usava outra ferramenta antes (vira `legado`, com a
   data da troca)?
4. **Gravar** `config/gestor` (`set`, ou `update` com `if_version` se já existe) com `prefixo_chave` (= `tipo`; no
   `generico`, o nome curto do serviço), `pendente: false` (só com o obrigatório da receita preenchido, testado e
   confirmado), `atualizado_em`. Só IDs e nomes; nunca token. Dizer em uma linha que o próximo `/bom-dia` traz os
   itens abertos.

## Varredura — juntar as fontes de gestão no quadro
O quadro é a fonte única para gerir tarefas e rotinas. Com o tempo, a pessoa pode ter pedido "salva isso" em várias
conversas, e instruções (e dados) ficaram espalhados, às vezes se contradizendo ("tarefas vivem no app X", "gerencie
por aqui"). Esta varredura acha esses pontos e propõe juntar tudo. **Só lê até o ok da pessoa.**

1. **Procurar** (só leitura), nos lugares de config da pessoa fora de repositório e na pasta atual:
   - o `CLAUDE.md` global (`<config>/CLAUDE.md`, com `<config>` = `$CLAUDE_CONFIG_DIR` ou `~/.claude`) e os
     `CLAUDE.md` da pasta atual e das pastas acima dela;
   - arquivos que esses `CLAUDE.md` citam por caminho (referências, guias);
   - memórias: `<config>/projects/*/memory/*.md`;
   - outras skills que concorrem pelo mesmo pedido (descrição que cobre "salvar/anotar tarefa" e não é `tarefas`).
   Critério: texto que manda registrar, gerir ou lembrar tarefas/pendências/rotinas em outro lugar (outro gestor,
   arquivo, "memória") ou descreve o processo da pessoa. Ignorar o que só descreve projeto ou pauta sem falar de tarefa.
2. **Mostrar uma lista curta** (arquivo, trecho de uma linha, o que ele manda) e perguntar numa mensagem só:
   "Encontrei N fontes de gestão fora do quadro, algumas se contradizem. O quadro junta tudo num lugar só. Quer que eu
   traga o que vale pro quadro e tire ou aponte essas referências pra ele?". A pessoa pode aceitar tudo, escolher, ou
   recusar. Nada achado → uma linha ("não achei instrução conflitante") e seguir.
3. **Com o ok, para cada item aceito:**
   - o processo, IDs, regras e formato que a pessoa já usa vão para `config/fontes` (campo certo, ou `texto`;
     `update` com `if_version`), acrescentando ao que já existe, sem apagar;
   - o que descreve o gestor externo (qual, o que nunca criar, quando escrever nele) vai para `config/gestor`.
     Se `config/fontes` e `config/gestor` descreverem o gestor de modos diferentes, vale o `config/gestor` (SCHEMA);
   - no arquivo de origem, remover ou trocar o trecho por uma linha apontando para o quadro. Antes de gravar em arquivo
     global (CLAUDE.md, referências), mostrar o diff.
   - **Nunca** copiar segredo, token ou senha para o quadro.
4. **Linha do CLAUDE.md global** (só com `automacao.linha_claude_md: true`). Garantir, com diff mostrado e ok, UMA
   linha no `<config>/CLAUDE.md` da pessoa (a raiz que vale para todas as pastas), no idioma dela: "Tarefas e
   pendências do usuário ficam no quadro `<nome>`, via skill `tarefas`." e, com gestor, como o gestor recebe trabalho
   (pelo `escrever` do `config/gestor`). Se já houver uma equivalente, não duplicar. Sem CLAUDE.md global, oferecer
   criar com só essa linha.
5. **Âncora de memória** (só com `automacao.ancora_memoria: true`) na pasta atual, como em `<skills>/tarefas/SKILL.md`
   § 0b. Se a conta do claude.ai tiver memória de usuário, sugerir à pessoa registrar ali a mesma frase; o Claude Code
   não escreve nela.
6. **Dizer o que mudou** em poucas linhas: o que foi para o quadro, o que foi tirado de onde, o que ficou como estava.

## Regras
- Nunca recriar um quadro que esta conta já alcança; no máximo abrir.
- A descoberta só lê: nenhuma escrita em conector durante a criação.
- A varredura nunca grava nem apaga nada sem o ok da pessoa, e nunca toca em código de repositório.
- Nunca copiar segredos para as preferências. Calendários, e-mails e identidades só os que o usuário confirmar.

---
name: quadro-tarefas
description: >
  Abre o quadro de tarefas do usuário (quadro em artefato com banco) no navegador; se ele ainda não existe
  nesta conta, cria: publica a página, grava preferências, gestor de tarefas, schema e índice, importa um pacote da
  tarefas-io se houver, e lembra o link no atalho local. Use quando pedirem
  "abre meu quadro", "quadro tarefas", "abre o quadro", "cria meu quadro de tarefas", "configura o quadro
  pra mim", "configura meu Linear/Jira/Notion no quadro", quando a skill tarefas disser que esta conta não tem
  quadro, ou para recriar o quadro na conta certa. Ao criar o quadro, também varre a máquina atrás de
  instruções antigas que mandam gerir tarefas em outro lugar (CLAUDE.md, referências, memórias, skills) e
  propõe juntar tudo no quadro ("varrer fontes", "tem instrução conflitante de tarefas"). Também veste o quadro
  com a marca da pessoa ou da empresa dela, a partir do site ou do guia de marca ("muda o tema do quadro",
  "coloca o quadro com a cara da minha empresa").
user_invocable: true
argument-hint: "(nenhum) | importar <pacote quadro-tarefas-*.json> | gestor (configurar o gestor de tarefas) | varrer (procurar instruções conflitantes) | tema [<site ou arquivo da marca>] (vestir o quadro com a marca)"
---

# quadro-tarefas — abrir ou criar o quadro

`<skills>` = a pasta-mãe do Base directory desta skill (vale em `~/.claude/skills` e dentro do plugin).

Arquivos: `<skills>/tarefas/app/` (`board-src.html`, `style-base.css`, `build.py`),
contrato em `<skills>/tarefas/SCHEMA.md`, como achar o quadro em `<skills>/tarefas/ACHAR-QUADRO.md`.
Pacotes de import/export (gerados pela `tarefas-io`): `~/.claude/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json`.

## 1. Já existe? Então só abre
1. Seguir `ACHAR-QUADRO.md` § Busca completa (lista de artefatos da conta).
   - **Achou:** o quadro existe nesta conta. Abrir no navegador (chamar `/quadro-tarefas` já é o pedido de abrir):
     `open <url>` no macOS (`xdg-open` no Linux, `start` no Windows; sem shell, só o link). Responder com o link e uma
     linha de estado (do `indice/ativos`: N abertas, N na Entrada). Sem `config/gestor` (e sem migração possível, ver
     `SCHEMA.md` § Migrações) ou com ele pendente → uma linha oferecendo configurar ou completar (§ Gestor). Fim. Não recriar.
   - **Argumento `gestor`:** achou o quadro → só o § Gestor (reconfigurar o que a pessoa pedir).
   - **Argumento `varrer`:** achou o quadro → só o § Varredura.
   - **Argumento `tema`** (ou pedido de mudar o visual): achou o quadro → só o § Tema.
   - **Não achou:** seguir para criar. Um quadro de outra conta (que não responde aqui) não conta: o desta conta
     é criado do zero ou a partir de um pacote exportado do outro.

## 2. Não existe: cria
1. **Pacote.** Se o usuário passou um, usar. Se existe algum `quadro-tarefas-*.json` em `~/.claude/tarefas-exports/`,
   oferecer importar o mais recente que pareça deste quadro (pelo `escopo`/`nome` das preferências do pacote). Sem pacote, começa vazio.
2. **Perguntar só o que falta** (uma pergunta, com padrões; com pacote, as preferências dele valem como padrão):
   idioma (`idioma`: o da pessoa, pelo jeito que ela escreve, ex. `pt-BR`, `en`; perguntar nesse idioma),
   nome (ex.: `Pessoais`, `Trabalho`), subtítulo, áreas (`{id, nome}`; uma área só esconde o filtro), tema (neutro, o padrão, ou o da
   marca: § Tema, passo 1 diz quando oferecer e como perguntar), agendas do `/bom-dia`,
   card automático por conversa (`criar_e_avisar` | `perguntar` | desligado), gestor de tarefas (§ Gestor; na mesma
   pergunta, só a ferramenta; os detalhes vêm depois).
3. **Montar a página:** `python3 <skills>/tarefas/app/build.py --titulo "Tarefas <Nome>" --out <scratchpad>/board-<escopo>.html`
   (o script checa o JS). Com tema da marca, antes fazer o § Tema passos 2 a 4 e acrescentar
   `--tema-arquivo <scratchpad>/tema-<escopo>.css` (e `--fontes "<url>"` se houver).
   **Tema efetivo** (um só, nesta ordem): o que a pessoa escolheu no passo 2 (marca nova ou neutro) → sem escolha e
   com pacote que traga `config/tema`, o do pacote (`css` no arquivo e `fontes` no `--fontes`) → neutro. `<escopo>` = `escopo` nas preferências: slug do nome, ou o do pacote importado (as fontes do
   `/bom-dia` e do `/boa-noite` vêm de `config/fontes`, ver `ACHAR-QUADRO.md` § Escopo). Nada da pessoa vai no HTML: a
   página lê de `config/preferencias`.
4. **Publicar** pelas regras da tool Artifact (quickstart `other` na primeira vez; publish com
   `capabilities: {"db": {}, "user": {}}`, `icon: "checklist"`, `description` de uma frase). O artefato pertence à
   conta desta sessão, e é por isso que só ela o acha depois.
5. **Semear o banco** (`batch`): `config/preferencias` (formato do SCHEMA, com `ignorar_titulos` padrão:
   `Bom dia`, `Boa noite`, nomes de rotinas agendadas), `config/schema` `{formato: "quadro-tarefas", versao: 3, escopo, criado_em, migracoes: []}`,
   `config/gestor` (§ Gestor; `{tipo: "nenhum"}` se a pessoa não usa), `indice/ativos` `{itens: {}, atualizado_em}`,
   e `config/tema` com o tema efetivo do passo 3, se ele não for o neutro (§ Tema, passo 6).
   Com pacote e `--com-config`, as preferências (e o `config/gestor`, se o pacote tiver) vêm do pacote (passo 6).
6. **Importar** o pacote seguindo a `tarefas-io` § Import (prévia → ok → gravar).
7. **Lembrar** no atalho local: `python3 <skills>/tarefas/quadros.py lembrar --url <url> --titulo "Tarefas <Nome>"`.
   Com pacote e `--com-config`, conferir que o `config/schema` gravado tem `formato: "quadro-tarefas"` (pacote antigo não tem: acrescentar),
   fazer a migração se a `versao` for antiga (`SCHEMA.md` § Migrações)
   e tirar `principal` das preferências importadas (o desempate é decidido nesta conta, não herdado do pacote).
   O import com `--com-config` também substitui `config/tema`: depois dele, regravar `config/tema` com o tema efetivo
   do passo 3 (ou apagá-lo, se o efetivo for o neutro), para o banco bater com a página publicada.
8. **Conferir e abrir:** um `list` de `tasks`, um `get` de `config/preferencias`, depois abrir no navegador como no § 1.
   Responder com o link, quantas tarefas entraram e, se havia um quadro antigo, que ele pode ser apagado depois de conferido.
9. **Varredura** (§ Varredura): o quadro acabou de nascer, então é a hora de juntar numa fonte só o que antes mandava
   gerir tarefas por outros caminhos.

## Tema — vestir o quadro com a marca da pessoa
O quadro nasce no tema neutro (`style-base.css`). Ele pode ganhar as cores, as fontes e o jeito da marca da
pessoa, em geral a da empresa dela. Nada de marca vem pronto no pacote: o tema é montado a partir do que a pessoa mostra.

1. **Quando oferecer e o que perguntar.** Na criação (§ 2, passo 2), dentro da mesma pergunta. Se houver contexto de
   empresa (e-mail corporativo nas agendas, conectores de trabalho ligados, nome de quadro como `Trabalho`, pasta de
   um repositório da empresa), oferecer assim: "Quer o quadro com a cara da sua empresa? Me manda o site (ou um guia
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
   - Fontes: se a família da marca existir no Google Fonts, montar a URL `https://fonts.googleapis.com/css2?family=…&display=swap`
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
   o CSS, a URL de fontes e de onde veio, para o quadro poder ser remontado igual (nova versão do plugin, troca de tema).
   Mostrar o print à pessoa e dizer em uma linha o que foi seguido (ex.: "azul e fonte do site da empresa; a fonte do
   logo é paga, usei a Inter no lugar"). Para voltar ao neutro: montar sem `--tema-arquivo`, publicar na mesma URL e
   apagar `config/tema`.

## Gestor — configurar `config/gestor`
Contrato em `SCHEMA.md` § `config/gestor`; receitas em `<skills>/tarefas/referencias/gestores/<tipo>.md`.
1. **Qual ferramenta:** sugerir pelos conectores ligados nesta sessão (tools do Linear → `linear`; Atlassian → `jira`;
   Notion → `notion`; vários → perguntar qual é o de tarefas). Uma pergunta só. "Não uso" → `{tipo: "nenhum"}`.
2. **Detalhes pelo conector, sem perguntar o que dá para ler:** seguir o § `config` da receita (time/projeto/base,
   status existentes). Propor o `mapa_status` a partir dos status lidos (sugestão da receita) e o padrão
   `escrever: {criar: "propor_no_boa_noite", editar: "propor_no_boa_noite"}`.
3. **Perguntar numa mensagem:** confirma o mapa e o modo de escrita? Tem regra da casa (label obrigatória, o que nunca
   criar, padrão de título)? Usava outra ferramenta antes (vira `legado`, com a data da troca)?
4. **Gravar** `config/gestor` (`set`, ou `update` com `if_version` se já existe) com `prefixo_chave` = `tipo`,
   `pendente: false` (só com o § Obrigatório da receita preenchido e confirmado), `atualizado_em`. Só IDs e nomes; nunca token. Dizer em uma linha que o próximo `/bom-dia` traz os itens abertos.

## Varredura — juntar as fontes de gestão no quadro
O quadro é a fonte única para gerir tarefas e rotinas. Com o tempo, a pessoa pediu "salva isso" em várias conversas e
o Claude espalhou instruções (e dados) por vários lugares, que podem se contradizer ("tarefas vivem no Notion", "gerencie
por aqui"). Esta varredura acha esses pontos e propõe juntar tudo. **Só lê até o ok da pessoa.**

1. **Procurar** (só leitura), nos lugares de config da pessoa fora de repositório e na pasta atual:
   - CLAUDE.md global (`~/.claude/CLAUDE.md`) e os CLAUDE.md da pasta atual e das pastas acima dela;
   - referências citadas por eles (ex.: `~/.config/**/references/*.md`);
   - memórias: `<config>/projects/*/memory/*.md` (`<config>` = `$CLAUDE_CONFIG_DIR` ou `~/.claude`);
   - outras skills que concorrem pelo mesmo pedido (descrição que cobre "salvar/anotar tarefa" e não é `tarefas`).
   Critério: texto que manda registrar, gerir ou lembrar tarefas/pendências/rotinas em outro lugar (Notion, Linear, Jira,
   Todoist, arquivo, "memória") ou descreve o processo da pessoa. Ignorar o que só descreve projeto ou pauta sem falar de tarefa.
2. **Mostrar uma lista curta** (arquivo, trecho de uma linha, o que ele manda) e perguntar numa mensagem só:
   "Encontrei N fontes de gestão fora do quadro, algumas se contradizem. O quadro junta tudo num lugar só. Quer que eu
   traga o que vale pro quadro e tire ou aponte essas referências pra ele?". A pessoa pode aceitar tudo, escolher, ou recusar.
3. **Com o ok, para cada item aceito:**
   - o processo, IDs, regras e formato que a pessoa já usa vão para o `texto` de `config/fontes` (`ArtifactData set` ou
     `update` com `if_version`; `{versao, texto, atualizado_em}`), acrescentando ao que já existe, sem apagar;
   - o que descreve o gestor externo (qual, o que nunca criar, "só por proposta do /boa-noite") vai para `config/gestor`.
     Se `config/fontes` e `config/gestor` descreverem o gestor de modos diferentes, vale o `config/gestor` (SCHEMA);
   - no arquivo de origem, remover ou trocar o trecho por uma linha apontando para o quadro. Antes de gravar em arquivo
     global (CLAUDE.md, referências), mostrar o diff.
   - **Nunca** copiar segredo, token ou senha para o quadro.
4. **Fechar com a linha do CLAUDE.md global.** Garantir, com diff mostrado e ok, UMA linha no `~/.claude/CLAUDE.md` da
   pessoa (a raiz que vale para todas as pastas): "Tarefas e pendências do usuário ficam no quadro `<nome>`, via skill
   `tarefas`. `<Gestor>` só por proposta do `/boa-noite`." (sem gestor: só a primeira frase). Se já houver uma
   equivalente, não duplicar. Se a pessoa não usa CLAUDE.md global, oferecer criar com só essa linha.
5. **Âncora de memória** na pasta atual, como em `<skills>/tarefas/SKILL.md` § 0b (as outras pastas recebem a âncora quando
   `tarefas` ou `/bom-dia` rodarem nelas). Se a conta do claude.ai tiver memória de usuário, sugerir à pessoa registrar
   ali a mesma frase; o Claude Code não escreve nela.
6. **Dizer o que mudou** em poucas linhas: o que foi para o quadro, o que foi tirado de onde, o que ficou como estava.
   Nada achado → uma linha ("não achei instrução conflitante") e seguir.

## Regras
- Nunca recriar um quadro que esta conta já alcança; no máximo abrir.
- A varredura nunca grava nem apaga nada sem o ok da pessoa, e nunca toca em código de repositório.
- Nunca copiar segredos para as preferências. Agendas e e-mails só os que o usuário confirmar.

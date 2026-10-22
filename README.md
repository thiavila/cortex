# Cortex

Um segundo cérebro para o Claude Code. O Cortex guarda suas tarefas num quadro que mora num artefato da sua própria
conta do Claude, liga cada conversa a um card, abre o seu dia com `/bom-dia` e fecha com `/boa-noite`.

*English: a task board that lives in an artifact in your own Claude account. One card per conversation, a morning
briefing (`bom-dia`) and an end-of-day wrap-up (`boa-noite`). The skills are written in Portuguese but work in your
language: when the board is created it detects your language, date format and time zone, and the board page itself
speaks Portuguese or English.*

> **Beta.** Feito para o app desktop do Claude (aba Code) no macOS e no Windows. Testado de ponta a ponta no macOS;
> no Windows e no Linux, os scripts foram testados nos caminhos de cada sistema. O Claude Code de terminal funciona
> onde a sua conta tiver as ferramentas de artefato no CLI (se `/artifacts` não existir aí, use o app).
> A página do quadro fala português e inglês; outros idiomas usam o inglês na página e o próprio idioma nas respostas.

## O que vem no plugin

| Skill | Para quê |
|---|---|
| `quadro-tarefas` | Cria o quadro na sua conta (ou abre, se já existe): descobre suas ferramentas, idioma e fuso, confirma em uma ou duas perguntas, configura o gestor de tarefas e, se quiser, veste o quadro com a marca da sua empresa. |
| `tarefas` | O quadro em si: salva, anota e acompanha tarefas ("anota pra depois", "add a card", "o que tem no quadro sobre X"). |
| `bom-dia` | Abre o dia: agenda, gestor de tarefas, reuniões e o que está parado viram o plano do dia. |
| `boa-noite` | Fecha o dia: resume cada conversa no card certo, propõe o que fechar e grava o diário. |
| `fechar` | Encerra a conversa atual: atualiza o card, registra no diário e arquiva a conversa (no app). |
| `tarefas-io` | Exporta e importa o quadro (JSON, CSV, Markdown, ou o seu gestor de tarefas). |

E um hook: na primeira mensagem de cada conversa, o Claude liga a conversa a um card do quadro (ou cria um na
Entrada). Dá para desligar ou mudar para "perguntar antes" dizendo isso numa conversa.

## Precisa de
- **O app desktop do Claude (aba Code)**, logado na sua conta do claude.ai. O quadro é um artefato com banco e
  precisa das ferramentas de artefato, que hoje vêm com o app. No terminal (CLI), só onde elas estiverem liberadas
  para a sua conta; sem elas, as skills avisam e não escrevem nada.
- **Python 3.8+**. No macOS vem com as Command Line Tools (`xcode-select --install`); no Windows, instale pelo
  python.org ou pela Microsoft Store (o Cortex acha `python3`, `python` ou `py -3`); no Linux, o da distribuição.
  Node é opcional.
- Os conectores que você já usa ligados no Claude (agenda, gestor de tarefas, gravador de reuniões, chat, código…).
  Nada é obrigatório: o Cortex usa o que encontrar.

Com as ferramentas de sessão do app, o Cortex também dá nome curto às conversas, arquiva as que terminaram e abre
conversas para o plano do dia (se você quiser). Sem elas (terminal com artefatos, por exemplo) essas partes ficam de
fora e o resto funciona igual: as conversas são lidas dos transcritos locais e viram cards com o comando
`claude --resume` para retomar.

## Instalar

No terminal:

```bash
claude plugin marketplace add thiavila/cortex
```

```bash
claude plugin install cortex@cortex
```

Ou, dentro do Claude Code, `/plugin marketplace add thiavila/cortex` e depois `/plugin install cortex@cortex`.

Depois reinicie o Claude (feche e abra o app, ou abra um terminal novo) e, numa conversa nova, rode
`/cortex:quadro-tarefas`. Ele procura as ferramentas ligadas, confirma com você o nome do quadro, o idioma, o fuso,
quais ferramentas usar e como o Claude deve trabalhar com o quadro, cria o quadro na sua conta e abre no navegador.

Para atualizar: `claude plugin marketplace update cortex`. Quadros criados na v0.2 são atualizados sozinhos na
primeira vez que uma skill escreve neles, mantendo o comportamento de antes.

## Usar
- `/cortex:bom-dia` de manhã e `/cortex:boa-noite` no fim do dia.
- "anota no quadro…", "o que tem no quadro sobre X", "marca como esperando" funcionam em qualquer conversa.
- **Gestor de tarefas** (Linear, Jira, Notion, ou qualquer outro com conector: Asana, ClickUp, GitHub Issues, Azure
  DevOps, Trello, Todoist…): `/cortex:quadro-tarefas gestor`. O que está aberto e atribuído a você lá vira card. O
  `/boa-noite` propõe o que criar ou atualizar na ferramenta e não grava nada sem o seu ok.
- **Ferramentas** (agenda, reuniões, chat, código): `/cortex:quadro-tarefas fontes` revê o que está ligado.
- **Tema**: `/cortex:quadro-tarefas tema https://suaempresa.com` veste o quadro com as cores e fontes do site (ou de um
  guia de marca em PDF ou print). Sem tema, o quadro fica no visual neutro.
- **Preferências**: diga numa conversa ("me pergunta antes de criar card", "não renomeia minhas conversas", "minha
  semana começa na segunda", "usa o Sonnet para os resumos") e fica gravado no quadro.

Tudo o que é seu (idioma, fuso, ferramentas, gestor, jeito de trabalhar) fica no banco do próprio quadro, não no
plugin. O contrato está em [`skills/tarefas/SCHEMA.md`](skills/tarefas/SCHEMA.md).

## Privacidade
O quadro é um artefato privado da sua conta: só você vê, a menos que compartilhe. Suas tarefas não saem do seu
Claude. A única coisa que a página carrega de fora são as fontes, do Google Fonts; para não carregar nada de fora,
peça "quadro sem fontes externas" (fica com as fontes do sistema).

## Licença
MIT

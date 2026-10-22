# Cortex

Um segundo cérebro para o Claude Code. O Cortex guarda suas tarefas num quadro que mora num artefato da sua própria
conta do Claude, liga cada conversa a um card, abre o seu dia com `/bom-dia` e fecha com `/boa-noite`.

*English: a task board that lives in an artifact in your own Claude account. One card per conversation, a morning
briefing (`bom-dia`) and an end-of-day wrap-up (`boa-noite`). The skills are written in Portuguese but answer in your
language: when the board is created it asks which one to use.*

> **Beta.** Testado no app desktop do Claude no macOS. Em andamento para a próxima versão: Windows e Linux, a
> página do quadro em outros idiomas (hoje os textos dela são em português), fuso e formato de data configuráveis,
> e a descoberta das suas ferramentas (agenda, reuniões, chat, gestor de tarefas) na criação do quadro.

## O que vem no plugin

| Skill | Para quê |
|---|---|
| `quadro-tarefas` | Cria o quadro na sua conta (ou abre, se já existe), configura o gestor de tarefas e veste o quadro com a marca da sua empresa. |
| `tarefas` | O quadro em si: salva, anota e acompanha tarefas ("anota pra depois", "cria um card", "o que tem no quadro sobre X"). |
| `bom-dia` | Abre o dia: agenda, gestor de tarefas, reuniões e o que está parado viram o plano do dia. |
| `boa-noite` | Fecha o dia: resume cada conversa no card certo, propõe o que fechar e grava o diário. |
| `fechar` | Encerra a conversa atual: atualiza o card, registra no diário e arquiva a conversa. |
| `tarefas-io` | Exporta e importa o quadro (JSON, CSV, Markdown, Linear, Jira, Notion, Todoist). |

E um hook: na primeira mensagem de cada conversa, o Claude liga a conversa a um card do quadro (ou cria um na
Entrada). Dá para desligar ou mudar para "perguntar antes" dizendo isso numa conversa.

## Precisa de
- **App do Claude para desktop (aba Code)**. O quadro é um artefato com banco, e o `/boa-noite` lê as conversas
  guardadas no computador, então ele não roda pelo claude.ai/code na web.
- `python3` no computador (o macOS já tem). Node é opcional.
- Os conectores que você já usa ligados no Claude (agenda, Linear, Jira, Notion, gravador de reuniões, Slack…).
  O `/bom-dia` usa o que encontrar.

## Instalar

No terminal:

```bash
claude plugin marketplace add thiavila/cortex
```

```bash
claude plugin install cortex@cortex
```

Ou, dentro do Claude Code, `/plugin marketplace add thiavila/cortex` e depois `/plugin install cortex@cortex`.

Depois feche e abra o app do Claude, e numa conversa nova rode `/cortex:quadro-tarefas`. Ele faz algumas perguntas
(idioma, nome do quadro, agendas, card automático por conversa, qual gestor de tarefas você usa e se quer o quadro com
a cara da sua empresa), cria o quadro na sua conta e abre no navegador.

Para atualizar: `claude plugin marketplace update cortex`.

## Usar
- `/cortex:bom-dia` de manhã e `/cortex:boa-noite` no fim do dia.
- "anota no quadro…", "o que tem no quadro sobre X", "marca como esperando" funcionam em qualquer conversa.
- **Gestor de tarefas** (Linear, Jira, Notion ou nenhum): `/cortex:quadro-tarefas gestor`. O que está aberto e
  atribuído a você lá vira card. O `/boa-noite` propõe o que criar ou atualizar na ferramenta e não grava nada sem o seu ok.
- **Tema**: `/cortex:quadro-tarefas tema https://suaempresa.com` veste o quadro com as cores e fontes do site (ou de um
  guia de marca em PDF ou print). Sem tema, o quadro fica no visual neutro.

## Privacidade
O quadro é um artefato privado da sua conta: só você vê, a menos que compartilhe. Suas tarefas não saem do seu
Claude. A única coisa que a página carrega de fora são as fontes, do Google Fonts.

## Licença
MIT

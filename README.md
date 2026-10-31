# Cortex

Um quadro de tarefas para continuar seu trabalho entre conversas e agentes, com `/bom-dia`, `/boa-noite`,
fechamento de conversa e import/export. No primeiro setup, o Cortex pergunta **quais agentes você usa**:

| Resposta | Quadro | Dados |
|---|---|---|
| Somente Claude | Artifact na conta Claude | Banco do artifact, como antes |
| Qualquer outro agente, sozinho ou junto com Claude | Interface no navegador local | SQLite compartilhado via CLI ou MCP |

**Não precisa hospedar um serviço na internet.** Não existe modo GPT Pages. A instalação disponibiliza as skills;
a pergunta acontece no primeiro `quadro-tarefas`. Usuários Claude existentes continuam no artifact até escolherem
explicitamente outro modo.

*English: a task board for your agents, with morning planning and end-of-day wrap-up. Claude-only users keep the
existing artifact. Any other agent selects a local SQLite board shared through CLI or MCP. No internet hosting.*

> **Beta v0.4.** A integração local é nova. Testes de protocolo não equivalem à validação em todos os aplicativos.
> O quadro fala português e inglês; respostas seguem o idioma escolhido. Outros idiomas usam inglês na interface.

## Skills

| Skill | Para quê |
|---|---|
| `quadro-tarefas` | Escolher agentes e perfil, configurar ou abrir quadro, fontes, gestor e tema. |
| `tarefas` | Salvar, anotar e acompanhar tarefas, ligando conversas aos cards. |
| `bom-dia` | Combinar agenda, tarefas e reuniões do escopo num plano do dia. |
| `boa-noite` | Resumir o trabalho disponível, propor fechamentos e registrar o diário. |
| `fechar` | Atualizar a tarefa e encerrar a conversa quando a plataforma permite. |
| `tarefas-io` | Exportar/importar JSON, CSV, Markdown e integrações de gestor. |

As regras são comuns; ferramentas de conversas, permissões e conectores são descobertos em cada agente.
Sem histórico de outras conversas, a rotina informa a cobertura e usa o contexto disponível.
O hook de primeira mensagem é específico do Claude; outros clientes podem invocar `tarefas` explicitamente.

## Instalar

No Claude Code:

```sh
claude plugin marketplace add thiavila/cortex
claude plugin install cortex@cortex
```

No Codex, depois de disponibilizada esta versão no marketplace:

```sh
codex plugin marketplace add thiavila/cortex
codex plugin add cortex@cortex
```

Para testar um checkout local no Codex, use `codex plugin marketplace add /caminho/absoluto/cortex` e depois
`codex plugin add cortex@cortex`. Reabra uma sessão e invoque `quadro-tarefas` (no Claude, `/cortex:quadro-tarefas`).
O pacote Codex contém as seis skills; o MCP é configurado depois, com o UUID real do quadro.
Outros clientes podem usar as mesmas skills e a CLI/MCP, pelo mecanismo de instalação que suportarem.

O modo artifact exige `Artifact` e `ArtifactData`, normalmente no app desktop Claude, aba Code. Sem essas
ferramentas o Cortex explica a limitação; não muda de backend silenciosamente.

O modo local precisa de Python com biblioteca padrão. Os comandos abaixo usam `python3`; substitua por `python`
ou `py -3` conforme a instalação. O lançador `sh skills/tarefas/py` também está disponível. Rode da pasta do Cortex.

## Configurar o quadro local

A skill pergunta agentes, perfil, nome, formato de data e fuso. Pelo terminal:

```sh
python3 skills/tarefas/setup.py --profile exemplo configure --agents claude codex --name "Meu quadro" --locale pt-BR --fuso America/Sao_Paulo
python3 skills/tarefas/setup.py --profile exemplo status
```

São exemplos: escolha seus valores. Qualquer nome além de Claude seleciona local. Sem `--agents`, o terminal
interativo pergunta; em uso por um agente, a pergunta acontece na conversa antes do comando.
O resultado contém um UUID `board`. Use o valor real:

```sh
python3 skills/tarefas/local.py --board <UUID> serve --port 0
python3 skills/tarefas/setup.py --profile exemplo mcp-config
```

O primeiro comando serve o quadro. Abra a URL impressa no navegador; ela só funciona nessa máquina e contém uma
credencial temporária no fragmento. Não a publique nem salve em cards. Encerrar o processo preserva as tarefas;
reiniciar gera nova URL. Nenhum daemon global é instalado.

O segundo **gera**, sem instalar, a entrada MCP com Python, caminho absoluto e UUID reais. Adicione-a à configuração
MCP de cada agente, preservando entradas existentes. Os dois devem usar o mesmo quadro e raiz. O navegador não
precisa estar aberto para usar CLI/MCP. Sem MCP, use `local.py --board <UUID> call` com JSON por stdin.
O contrato e a tradução de operações das skills estão em [`LOCAL.md`](skills/tarefas/LOCAL.md).

## Roteamento opcional por conta do agente

A seleção automática pode ser habilitada por pessoa/empresa em `config/roteamento` no banco de cada quadro.
`setup.py resolve --host claude` consulta a conta autenticada no host e escolhe apenas uma correspondência.
Sem regras ativas, mantém o fluxo habitual. Havendo regras sem correspondência ou ambíguas, pede escolha explícita. Contas e empresas concretas nunca entram nas skills.
As regras Claude não são usadas pelo Codex ou por outro host. Contrato e exemplo em `LOCAL.md`.

## Dados, perfis e migração

A raiz local é `CORTEX_LOCAL_DIR` quando definido, ou:

- macOS: `~/Library/Application Support/Cortex`.
- Windows: `%LOCALAPPDATA%/Cortex`.
- Linux: `$XDG_DATA_HOME/cortex` ou `~/.local/share/cortex`.

Use `--root <pasta>` antes do comando para escolher outra raiz, de forma consistente no setup, CLI, servidor,
MCP e import/export. A seleção fica em `profiles/<perfil>.json`. `CORTEX_PROFILE` pode definir um perfil escolhido
explicitamente. **Perfil local não é conta autenticada**: separe trabalho e pessoal e confira as contas dos
conectores. Não é inferido pelo projeto ou por `CLAUDE_CONFIG_DIR`.

Repetir setup preserva o quadro. Trocar modo requer confirmação e `--replace-selection`; isso só altera a seleção,
sem migrar nem apagar o anterior. Para vir de artifact, exporte com `tarefas-io` numa sessão Claude com acesso,
crie um quadro local vazio e confira a prévia:

```sh
python3 skills/tarefas/local_io.py --board <UUID> import --input <pacote.json>
python3 skills/tarefas/local_io.py --board <UUID> import --input <pacote.json> --apply
python3 skills/tarefas/local_io.py --board <UUID> export --out <backup.json>
```

Execute `--apply` apenas depois da aprovação da prévia. Importação é para quadro novo vazio; o artifact de origem
permanece intacto. Dados, preferências, recorrentes e diário seguem o contrato de exportação.

## Privacidade

No artifact, os dados ficam na conta Claude e seguem suas permissões. No local, ficam no computador; os agentes
recebem o conteúdo necessário às operações solicitadas, conforme seus próprios serviços. Quem tem acesso aos
arquivos da conta do sistema pode acessar o banco: perfis não isolam usuários do sistema. Mantenha backup privado.

O servidor escuta apenas `127.0.0.1`, verifica Host/Origin e exige autorização para dados. Não habilita CORS público.
O MCP não oferece shell nem acesso arbitrário a arquivos. O modo local começa com fontes do sistema. Um tema importado com `fontes_externas: true` preserva suas fontes do Google Fonts; somente os domínios de CSS/fontes do Google são liberados. Os dados continuam no computador. Não publique banco, exports ou URL temporária do quadro.

## Desenvolvimento

```sh
python3 -m unittest discover -s tests -v
claude plugin validate .
```

Use dados temporários nos testes. Modelo em [`SCHEMA.md`](skills/tarefas/SCHEMA.md), seleção e transporte em
[`LOCAL.md`](skills/tarefas/LOCAL.md). A versão não instala serviço nem muda quadros existentes automaticamente.

## Licença

MIT

## Serviço opcional para vários quadros

`service.py --config <arquivo.json> --status <arquivo-privado.json>` serve vários quadros num único processo. Configuração: `{root:"<raiz>",boards:{exemplo:{board:"<UUID>",port:0}}}`. Em repouso, usa espera bloqueante do sistema, sem polling. Status deve ficar numa pasta privada; contém URLs com credenciais temporárias. `--status <arquivo> --open <chave>` abre o quadro no macOS.

Um LaunchAgent por usuário pode invocá-lo no login com RunAtLoad e throttle, sem abrir browser. É opcional e não é instalado automaticamente pelo plugin. Após restart, reabrir pela URL nova/atalho. O atendimento é sequencial e uma conexão sem dados pode reter o serviço por até5s.

### Abas fixas (opt-in do serviço)

Com portas fixas, `persistent_auth: true` no JSON do serviço mantém uma chave por quadro em `<root>/browser-auth/` (0700/0600). O browser guarda apenas a credencial validada em localStorage daquele quadro/origem. Autorize uma vez pela URL do atalho; depois fixe o endereço raiz sem fragmento. Reiniciar o serviço mantém a autorização. O modo CLI padrão continua efêmero.

Se limpar os dados do browser ou mudar de perfil, reabra pelo atalho para autorizar novamente. Revogar exige parar o serviço, remover a chave privada do quadro e iniciar novamente. Não publique as chaves. Uma origem loopback persistente deve ser usada somente num computador confiável: outro processo que ocupe a mesma porta enquanto o serviço estiver parado pode capturar o armazenamento dessa origem.

O favicon de cada quadro pode ser definido em `config/tema.favicon`: basename de PNG/ICO em `<root>/assets` (máximo1MiB). Os logos ficam na instalação da pessoa; o código não contém marcas fixas. Reinicie o serviço e recarregue a aba para aplicar; a URL do favicon inclui hash para atualizar o cache.

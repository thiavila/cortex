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

### Lembretes e verificação no Codex (0.4.5)

O pacote inclui `hooks/codex.json`: `UserPromptSubmit` e `SessionStart` (`startup`, `resume`, `compact`). O lembrete pede vínculo com um card e registro de marcos, respeitando as preferências, o modo perguntar, escopo somente leitura e exclusões. Não cria tarefas, não lê transcritos e não chama LLM. Não há hook Stop nem continuação automática de modelo.

**Copiar os arquivos não significa instalação operacional.** O instalador retorna `ready:false` e `verification_required` até uma verificação explícita. Não muda confiança nem edita `config.toml`. Revise as definições em **Codex Settings > Hooks** ou `/hooks` e confira o caminho, evento e comando. Atualizar uma definição pode exigir nova aprovação. Nunca forje hashes de confiança para contornar essa etapa.

Quem carrega somente as skills pode instalar o adapter separado (macOS/Linux/WSL):

```sh
python3 scripts/install_codex_hooks.py --observe
# Instalar e verificar usando uma conversa real já existente:
python3 scripts/install_codex_hooks.py --observe --verify --cwd /caminho/absoluto/do/projeto --session-id ID-DA-CONVERSA
# Verificação independente, sem instalar nem escrever no quadro:
python3 skills/tarefas/codex_harness.py doctor --cwd /caminho/absoluto/do/projeto --session-id ID-DA-CONVERSA
# Somente comprovar o vínculo persistido conversa ↔ card:
python3 skills/tarefas/codex_harness.py verify --cwd /caminho/absoluto/do/projeto --session-id ID-DA-CONVERSA
# Remover só as definições exatas de propriedade do instalador:
python3 scripts/install_codex_hooks.py --remove
```

`--codex-home` seleciona explicitamente outro host; `--root`/`--profile` selecionam o quadro para a verificação. Sem perfil explícito, `doctor`/`verify` usam somente as regras Codex cadastradas para a pasta da sessão. Falta/ambiguidade de seleção é erro: nenhum quadro ou card é criado como fallback. Perfil artifact recebe orientação para seu adapter; o verificador local não o substitui.

O `doctor` verifica separadamente: snapshot versus arquivos fonte atuais; descoberta real `hooks/list` do Codex; os dois eventos habilitados e confiáveis, sem duplicatas; seleção do quadro e leitura das preferências; comprovante recente de execução; e vínculo lido novamente do card e do índice. Não deduz confiança pela posição em um arquivo. Se o protocolo nativo não estiver disponível, informa indisponível, sem aprovar por aproximação. No modo nativo, a versão instalada ainda não é comparada à fonte: informa `native_version_unverified` e mantém o diagnóstico incompleto, inclusive após remover o standalone. Requer o Codex CLI para inspecionar o host; a inspeção não cria conversas nem chama modelo. `--verify` retorna código2 enquanto faltar uma etapa. `runtime_ready` sozinho não comprova registro de tarefas.

**Comprovantes locais:** `--observe` no instalador standalone habilita metadados privados em `<CODEX_HOME>/cortex-hooks/observations/`; no adapter nativo a observação está ativa por padrão e consta no comando a ser revisado. Contêm somente hash da identidade da sessão, evento, horário, emissão/exclusão e hash do script; nunca texto do prompt, transcrito, título, conteúdo do card ou credenciais. Arquivos0600, diretório0700, até512 comprovantes. Execução excluída é registrada como tal e não vira prova de emissão. `doctor` exige evento `UserPromptSubmit` das últimas24h e do mesmo código. Metadado prova execução local, **não obediência do modelo**; rodar o script manualmente não é teste de entrega pelo host. Sem `--observe`, o standalone continua sem gravar metadados e o diagnóstico não afirma entrega observada.

A cópia em `<CODEX_HOME>/cortex-hooks/runtime/` preserva outros hooks, recebe backup e é imutável por digest. O `doctor` compara com a versão fonte a partir da qual foi chamado; para verificar atualização, invoque o helper da versão nova do plugin. Repetir instalação não duplica definições. Atualizações interrompidas são retomáveis; alterações manuais exigem reconciliação explícita. Use **um** modo: plugin nativo ou instalação standalone. Atualize também o snapshot ao atualizar skills; remover os hooks preserva backups para recuperação.

**Aceite da instalação:** após revisão/confiança, envie uma mensagem de trabalho real numa conversa principal existente. O agente resolve o quadro, encontra ou registra o card conforme autorização/preferências e executa `verify` para reler o vínculo. Só depois `doctor --session-id` pode mostrar os quatro estágios verificados. Teste retomada e compactação sem duplicar cards; uma consulta somente leitura/delegada não pode escrever no quadro para satisfazer esse teste. Para testar criação sem trabalho real, use um quadro isolado e descartável com autorização — o instalador não semeia cards de teste no quadro pessoal.

Memórias e instruções globais permanecem intactas. O diagnóstico torna falhas explícitas e o agente só confirma gravação depois do read-back; não promete que um lembrete isolado garante todos os marcos sem execução do fluxo.
O pacote Codex contém as seis skills; o MCP é configurado depois, com o UUID real do quadro.
Outros clientes podem usar as mesmas skills e a CLI/MCP, pelo mecanismo de instalação que suportarem.

### Validação antes de publicar alterações

Use `make ci` para os testes Python/Node e os contratos de empacotamento. Depois de commitar em uma branch
que contém a main atual, `make ci-local` testa uma cópia limpa do commit, registra o status `local-ci` e faz
o push. `bash scripts/ci/local-ci.sh --dry-run` testa sem publicar. O CI oficial executa os mesmos checks
em Linux; como são baratos, continuam rodando mesmo com atestado local. PRs draft não executam os jobs.

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

## Roteamento opcional por pasta ou conta do agente

A seleção automática pode ser habilitada por pessoa/empresa em `config/roteamento` no banco de cada quadro.
`setup.py resolve --host claude --cwd <pasta>` escolhe primeiro pela pasta da sessão (regras com `pastas`, a mais
profunda vence) e, sem regra de pasta, pela conta autenticada no host. Só aceita uma correspondência.
Regra de pasta serve para quem usa a mesma conta em escopos diferentes, como trabalho e pessoal.
Sem regras ativas, mantém o fluxo habitual. Havendo regras sem correspondência ou ambíguas, pede escolha explícita. Contas e empresas concretas nunca entram nas skills.
No Codex, use `setup.py resolve --host codex --cwd <pasta absoluta da sessão>` (`--cwd` obrigatório) com regras próprias `host:"codex"`. O Codex resolve por pasta sem consultar o login Claude; regras por conta pedem seleção explícita. Regras de um host não são herdadas por outro. Contrato e exemplo em `LOCAL.md`.

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

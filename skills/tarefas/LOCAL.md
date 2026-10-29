# Cortex local — seleção, dados e ferramentas

Esta referência precede as instruções específicas de artifacts nas seis skills. A mesma regra de tarefa,
diário e preferência vale nos dois modos; o transporte e a identidade do quadro mudam.

## Escolha no primeiro setup

A instalação disponibiliza as skills. **A pergunta acontece no primeiro `quadro-tarefas`**, antes de exigir
`Artifact`/`ArtifactData`: “Quais agentes você usa: somente Claude, ou também/outro como Codex, Gemini…?”.
Traduzir para o idioma da pessoa. Não deduzir a resposta pelo aplicativo atual ou pelos agentes instalados.

- Resposta **somente Claude** → `artifact`, como antes. Continua necessário ter ferramentas de artifacts.
- Resposta com **qualquer outro agente**, sozinho ou com Claude → `local`.
- Não existe modo Pages. Falta de uma ferramenta não autoriza trocar de modo silenciosamente.

Confirmar um perfil local curto (ex.: `pessoal` ou `trabalho`), nome do quadro, locale e fuso. Perfil é uma escolha
da pessoa, **não prova da conta autenticada**. Dois aplicativos devem selecionar o mesmo perfil/raiz para dividir
o quadro. Nunca inferir perfil por cwd, nome da empresa, `CLAUDE_CONFIG_DIR` ou conta de um conector.

`<skills>` é a pasta que contém `tarefas`; `<root>` é a raiz local independente de Claude:
`CORTEX_LOCAL_DIR`, senão Application Support/Cortex no macOS, LOCALAPPDATA/Cortex no Windows ou
XDG_DATA_HOME/cortex no Linux (com os padrões do sistema). Dados ficam fora do plugin/repositório.

Ler a seleção sem efeitos colaterais:

```sh
python3 <skills>/tarefas/setup.py --profile <perfil> status
```

Também aceita `CORTEX_PROFILE`, definido explicitamente pela pessoa. Sem perfil conhecido, perguntar qual usar;
não procurar todos os bancos para escolher o primeiro. Um caminho `--root` pode ser fornecido antes do comando.

Para gravar as respostas confirmadas:

```sh
python3 <skills>/tarefas/setup.py --profile <perfil> configure --agents claude
python3 <skills>/tarefas/setup.py --profile <perfil> configure --agents claude codex --name '<nome>' --locale '<locale>' --fuso '<IANA>'
```

No terminal interativo, omitir `--agents` faz a própria CLI perguntar; em execução sem terminal, a skill pergunta
e passa a resposta. Nome/locale/fuso são exigidos ao criar o quadro local. Use o Python disponível (`python3`,
`python` ou `py -3`; o lançador `sh <skills>/tarefas/py` continua disponível).

Repetir setup do mesmo modo preserva o ID e os dados, inclusive se mudar a lista de agentes. Trocar de modo exige
consentimento explícito e `--replace-selection`; só altera a seleção, **não migra nem apaga o quadro anterior**.
Use outro perfil para manter ambos. Depois de trocar para local, ofereça export/import do artifact com prévia.

**Compatibilidade anterior:** sem seleção nova, usuários Claude com ferramentas de artifacts continuam no fluxo
`ACHAR-QUADRO.md`. Em um agente sem essas ferramentas, iniciar o setup; não interpretar “sem configuração” como
permissão para criar um banco. Seleção inválida/inacessível é erro, não motivo para fallback.

## Quando backend é local

Usar `board` da seleção, nunca URL de artifact. A identidade é `(raiz local, board UUID)`; o nome é só apresentação.
Ler `config/preferencias` e validar o escopo antes de coletar conectores. Cada conector mantém sua própria conta;
acesso local ao computador não comprova acesso à conta Pessoal/Trabalho do serviço.

```sh
python3 <skills>/tarefas/local.py --board <UUID> call < pedido.json
python3 <skills>/tarefas/local.py --board <UUID> serve --port 0
```

Passe o mesmo `--root <root>` usado no setup, se customizado, antes do comando. `call` recebe JSON por stdin;
escreva o JSON com ferramenta de arquivo, não interpolando texto de tarefa no shell. O servidor imprime a URL
de abertura. Abra-a no navegador pelo mecanismo da plataforma. Ele só escuta `127.0.0.1`; o fragmento da URL
contém a credencial daquela execução. Não publicar, registrar em cards ou compartilhar essa URL; ela é temporária.
O processo fica ativo enquanto a tela é usada. Encerrar o processo preserva o SQLite; iniciar novamente gera nova URL.
Não instalar daemon, abrir porta na rede ou iniciar serviço escondido só para ler tarefas pela CLI/MCP.

### Tradução de ArtifactData

Nos passos das skills, substitua a tool pelo dispatcher local. Não chamar `Artifact list`, `Artifact publish`,
`quadros.py lembrar`, descoberta `mine`, migrações de artifact ou `window.claude` neste modo.

| Operação da skill | Pedido local |
|---|---|
| `get tasks/<id>` | `{"op":"get","collection":"tasks","id":"<id>"}` |
| listar coleção | `{"op":"list","collection":"tasks","limit":100}`; continuar `next_cursor` |
| criar documento | `{"op":"set","collection":"tasks","id":"<id>","data":{...}}` |
| atualizar existente | `{"op":"update","collection":"tasks","id":"<id>","data":{...},"if_version":<versão>}` |
| excluir existente | `{"op":"delete","collection":"tasks","id":"<id>","if_version":<versão>}` |
| lote | `{"op":"batch","operations":[...],"mutation_id":"<id estável do pedido>"}` |
| reconstruir índice | `{"op":"rebuild-index"}` |

`get` retorna `{id, exists, data, version}`; listas retornam `{docs:[...], next_cursor}`. `exists:false` não é erro
de acesso. Criação não substitui um documento existente. Toda alteração/exclusão usa a versão recém-lida;
conflito → reler e reconciliar, nunca retirar `if_version`. Arrays precisam preservar dados atuais ao fazer união.
Repetir uma escrita com resultado ambíguo usa o mesmo `mutation_id` e conteúdo; não gerar ID novo antes de reconciliar.
Confira erros do processo e recibos antes de informar sucesso. Filtros só conforme schemas anunciados no MCP;
sem operador suportado, listar paginado e filtrar no agente, sem ignorar a condição do usuário.

**Índice local é derivado e transacional.** Pular todas as escritas manuais em `indice/ativos` descritas nas
skills antigas; o servidor o mantém ao gravar tarefas. No `/boa-noite`, usar `rebuild-index` quando necessário.
Não incluir gravação do índice em lotes locais. Mesma regra para a página e imports.

O setup inicializa o banco; o assistente completa preferências/fontes/gestor com as respostas da pessoa usando
`get` + `update` versionado, mantendo o schema suportado pelo runtime. A página é servida dos arquivos do plugin;
atualizar o plugin não recria o banco. Tema usa `config/tema`; não publicar outro artifact para mudar o visual local.

### MCP opcional

```sh
python3 <skills>/tarefas/setup.py --profile <perfil> mcp-config
```

Esse comando **gera**, sem instalar, JSON de configuração com o Python, caminho absoluto e UUID reais. Adicionar
a entrada `cortex` à configuração MCP do aplicativo pelo procedimento suportado, preservando as entradas existentes.
Não configurar placeholders como se fossem executáveis. Iniciar com `local.py --root <root> --board <UUID> mcp`.
Cada processo está vinculado a um quadro; configurar outro perfil exige outra entrada/seleção explícita. O MCP usa
o mesmo dispatcher da CLI e não exige manter o navegador aberto. Sem MCP, as skills funcionam pela CLI.

## Conversas e rotinas por capacidade

No modo local, nomear identidades por plataforma: `claude:<id>`, `codex:<id>` ou `<agente>:<id>`; a chave externa
é `conversa:<identidade>`. Preservar IDs antigos de artifacts importados. Nunca tratar UUID do Codex como CLI Claude.
Guardar links/comandos de retomada apenas quando a plataforma os fornecer ou documentar; sem eles, `link:null`.

- **Codex desktop:** descobrir `list_threads`, `read_thread`, `set_thread_title`, `set_thread_archived` e ferramentas
  de automação disponíveis. Ler as conversas elegíveis do escopo; resumir só texto necessário. Criar chats ou enviar
  mensagens para outros chats somente com autorização explícita do usuário, mesmo se uma preferência antiga disser
  `chips`. Não escrever nas memórias/instruções do Codex por analogia com `CLAUDE.md`.
- **Claude:** usar as ferramentas de sessão quando disponíveis; o extrator `boa-noite/conversas.py` é exclusivo
  de transcritos Claude. Seu `--quadro` recebe o UUID local para separar cursores.
- **Outros agentes/CLI:** usar somente ferramentas realmente expostas. Sem leitura de histórico, resumir a conversa
  atual e avisar a cobertura limitada. Não varrer diretórios privados de outros agentes ou inventar ferramentas.

No `/boa-noite`, marque o trecho resumido por plataforma/conversa no diário e só avance o cursor depois de persistir
o resumo. Isso evita repetir fechamentos quando o histórico é relido. Arquivar/renomear continua condicionado às
preferências e às permissões do host. Hook automático do Claude não implica hook equivalente nos outros agentes;
até existir integração validada, ligar o card ao invocar a skill. Memória/instruções globais só com pedido explícito.

## Exportar e migrar

```sh
python3 <skills>/tarefas/local_io.py --root <root> --board <UUID> export --out <pacote.json>
python3 <skills>/tarefas/local_io.py --root <root> --board <UUID> import --input <pacote.json>
python3 <skills>/tarefas/local_io.py --root <root> --board <UUID> import --input <pacote.json> --apply
```

Import sem `--apply` é prévia. Aplicar somente após confirmar a prévia e somente em quadro novo vazio, conforme a
validação do comando. Para vir de artifact, exportar primeiro com `tarefas-io` na sessão Claude que tem acesso.
Não executar `writes-N.json` do `io.py` legado diretamente no dispatcher: `file_path` não é uma operação remota.
Nunca apagar ou desativar o quadro de origem automaticamente. Dados ficam no computador e o usuário cuida do
backup; exportações contêm conteúdo privado e não entram no repositório público.

# Cortex v0.3 — diligência de agnosticismo

Objetivo: o Cortex funcionar para qualquer pessoa, de qualquer empresa, em qualquer idioma e máquina. Tudo o que é
específico de uma pessoa ou empresa vem do banco do quadro (`config/*`), descoberto ou perguntado na criação, e não
fica fixo nas skills, nos scripts nem na página.

Fonte: duas auditorias independentes de 22/10/2026 (Claude Opus e Codex/GPT) sobre o commit da v0.2, juntadas aqui.

## Decisões do dono (22/10)
1. **Colunas:** as 5 de hoje ficam como padrão (`entrada`, `a_fazer`, `fazendo`, `esperando`, `feito`). Os ids não
   mudam; os nomes na tela seguem o idioma do quadro. Quem quiser outra coisa altera a própria skill.
2. **Um quadro por conta do Claude** (como hoje). Áreas separam os assuntos dentro do quadro.
3. **Plataformas:** macOS, Windows e Linux, no app desktop e no CLI. Onde faltar uma ferramenta do app desktop,
   a skill segue sem ela, sem quebrar.
4. **Repo público desde a v0.2** (beta). A v0.3 sai como atualização.

## 1. Portabilidade (P0)
- `boa-noite/conversas.py`: lê `~/Library/Application Support/<app>/claude-code-sessions` (só macOS) e um layout
  interno do app (`<conta>/<org>/local_*.json`) e o deep link `claude://claude.ai/epitaxy/<id>` (também em
  `board-src.html` e `SCHEMA.md`). Fazer: caminho por SO (`%APPDATA%\Claude` no Windows, `~/.config/Claude` no
  Linux), manter `--app-dir`, isolar o que depende do app numa função com erro claro e, se falhar, cair em
  `list_sessions` + `list_events`. Corrigir o corte de data (UTC × data local, `conversas.py:118`).
- `tarefas/quadros.py`: `fcntl` não existe no Windows → lock portátil (`msvcrt` ou arquivo com `O_EXCL`).
- `python3` fixo no hook e nas skills → lançador que tenta `python3`, `python`, `py -3`; corrigir o README
  ("o macOS já tem" só vale com as Command Line Tools).
- Ferramentas só do app desktop (`get_session`, `set_session_title`, `list_sessions`, `list_events`,
  `archive_session`, `send_message`, `spawn_task`, `list_scheduled_tasks`): passo de capacidades em
  `ACHAR-QUADRO.md` § 0, com o que fazer sem cada uma. O hook passa `session_id` e `cwd` no `additionalContext`.
  No CLI, a conversa vira `conversa:cli:<id>`.
- Caminhos de estado fixos em `~/.claude` (hook, `conversas.py`, `quadros.py`, exports, `fontes-<escopo>.md`,
  `CLAUDE.md`): um resolvedor só, `${CLAUDE_PLUGIN_DATA}` (conferir se existe) → `$CLAUDE_CONFIG_DIR` → `~/.claude`.

## 2. Idioma, data e fuso (P1)
- `board-src.html` tem ~120 textos fixos em português e nunca lê `config/preferencias.idioma`. Fazer: dicionário
  na página (pt-BR e en; en como reserva), `t(chave)` em todo texto, inclusive acessibilidade, erros e recorrentes.
- Textos gravados em português independentemente do idioma: histórico da página ("Criada no quadro",
  "Status: X → Y"…), `recorrentes.py`, `io.py` (prévia, export Markdown). Passar `idioma` aos scripts.
- Datas DD/MM fixas (página, `^15/10` no quick-add, títulos "☀️ Bom dia seg 28/09", "Concluído em DD/MM" no gestor),
  dias da semana em português, `localeCompare(..., "pt")`, sem fuso. Fazer: `config/preferencias.locale` (BCP-47),
  `fuso` (IANA), `semana_inicia`; datas via `Intl`; quick-add aceita ISO e o formato do locale; `!high` etc.
- Achar o quadro depende do título começar com `Tarefas`: identificar só por `config/schema.formato`
  (ou prefixo neutro).
- `ignorar_titulos` padrão em português ("Bom dia", "Boa noite") → pular por comando/marcador, como o hook já faz.
- Slugs só ASCII: nomes de projeto em chinês, árabe etc. somem. Normalização Unicode ou id opaco.

## 3. Ferramentas dadas como certas (P1)
- Granola como gravador padrão (`bom-dia`, `boa-noite`) → qualquer conector de reunião descoberto, em `config/fontes`.
- `gcal:` como prefixo de chave → `agenda:<id>` ou prefixo vindo de `config/fontes`.
- Haiku fixo no resumo do `/boa-noite` (e `custo.modelo: "haiku"` no SCHEMA) → `config/preferencias.resumo`
  `{modelo: null|…, confirmar_acima}`; `null` = modelo padrão de subagente.
- Gestor só `linear|jira|notion|nenhum` → `tipo: "generico"` com a receita descoberta pelo conector e guardada em
  `config/gestor.receita` (Asana, ClickUp, GitHub Issues, Azure DevOps, Trello, Todoist, Monday…).
  Filtros de leitura (`config/gestor.leitura`) além de "atribuído a mim".
- `config/fontes` é texto livre, sem seção no SCHEMA e nunca semeado. Fazer v2 estruturada:
  `{agenda:{conector, calendarios[]}, reunioes:{conector}, chat:[…], email, codigo:{host, repos[]}, conversas:{backend},
  outras:[], texto}`, com a identidade da pessoa em cada ferramenta (`eu`). Tirar a referência a
  `config/preferencias.fontes.repos`, que não existe.
- Google Fonts sempre carregado → opção de fontes do sistema (`config/tema.fontes_externas: false`).

## 4. O jeito do autor escrito como regra (P1)
- Git/PR como certo: `origin/main` fixo, `cp -p` para o checkout principal, "PR mergeado = entregue", lista de ruído
  `.gemini/skills, AGENTS.md, GEMINI.md`. Fazer: `config/preferencias.codigo`
  `{usa_git, remoto, branch_base, ruido[], copiar_fora_do_git}`; sem git, pular toda evidência de git/PR.
- Automação no gosto do autor: `/bom-dia` abre conversa para todo item escolhido ("obrigatório"), conversas
  renomeadas e arquivadas, âncora de memória em toda pasta, linha no `CLAUDE.md` global. Fazer:
  `config/preferencias.automacao {encaminhar_plano: chips|perguntar|nao, renomear_conversas, arquivar_conversas,
  ancora_memoria, linha_claude_md}`, perguntado na criação.
- Política na descrição da `tarefas` ("nunca mandar direto para Notion, Linear ou Jira") → derivar de
  `config/gestor.escrever` e reescrever neutro.
- Regras de fechamento do `/boa-noite` (esperando o usuário que não voltou = encerrada; data passada = feita) →
  `config/preferencias.regras_fechamento`, padrão = só com evidência explícita.
- Modo `perguntar` do card por conversa não é respeitado: a `tarefas` § 1 grava antes de olhar o modo. Corrigir.
- Traços do autor: `~/.config/**/references/*.md`, `~/Github` como raiz padrão, "agente-cargo, monitor",
  exemplos locais (CNPJ, "Fechar o financeiro", `🛠️ Ferramentas`, `🌴 Pessoal`). Neutralizar.
- `recorrentes.py` usa área `geral` quando falta; a página usa a primeira área → `config/preferencias.area_padrao`.
- Pessoas casadas pelo primeiro nome sem acento → identidades/aliases em `config/fontes`.

## 5. Histórico e ruído (P2)
- Decisões datadas no texto ("decidido em 14/10", "pedido de 20/10", "antes de 05/10"): tirar a data, manter a
  regra ou virar preferência.
- Migrações v1→v3, campo `export` obsoleto, `fontes-<escopo>.md`, `DIARIO-*.md`: mover para `MIGRACOES.md`,
  lido só quando `versao < 3`. Quadro novo nasce na versão atual.
- Campos usados e não documentados: `exemplo_projeto`, `titulo_conversa.manter`.

## 6. Criação do quadro (`quadro-tarefas` § 2) — o que falta perguntar ou descobrir
| Falta | Onde fica | Como |
|---|---|---|
| locale, fuso, início da semana | `preferencias.locale`, `fuso`, `semana_inicia` | inferir do idioma e do sistema; confirmar |
| dias úteis e horário | `preferencias.dias_uteis`, `horario` | perguntar com padrão |
| agenda, reuniões, chat, código, conversas | `config/fontes` (estruturado) | descobrir pelos conectores ligados; confirmar |
| usa git/PR, branch base, remoto | `preferencias.codigo` | perguntar; branch pelo git da pasta |
| raízes de projetos | `config/projetos.raizes` | descobrir; confirmar |
| automação (abrir conversas, renomear, arquivar, memória, CLAUDE.md, `fechar.modo`) | `preferencias.automacao` | uma pergunta agrupada |
| modelo do resumo e teto de custo | `preferencias.resumo` | padrão, avisado uma vez |
| gestor fora das 3 receitas | `config/gestor.tipo: "generico"` + `receita` | descobrir pelo conector |
| quem é a pessoa em cada ferramenta | `config/fontes.*.eu` | chamadas "me" dos conectores |
Depois de importar um pacote, reconfirmar `config/fontes`, `config/gestor` e `config/projetos` (outra máquina ou empresa).
A criação confere as capacidades antes e verifica as escolhas pelos seus consumidores no fim.

## Plano (ordem)
1. **Portabilidade:** conversas por SO com reserva, lock portátil, lançador de Python, passo de capacidades,
   resolvedor de caminhos, hook com `session_id`/`cwd`.
2. **Contrato:** SCHEMA v4 com os campos novos de `preferencias`, `config/fontes` estruturado, gestor genérico,
   campos não documentados; migrações antigas para `MIGRACOES.md`; migração v3→v4 para quadros existentes.
3. **Idioma:** dicionário na página e nos scripts, datas via `Intl`, fuso, quadro achado sem depender do título,
   slugs Unicode.
4. **Despersonalizar as skills:** Granola/gcal/Haiku via config; git/PR atrás de `codigo.usa_git`; automações atrás
   de `automacao`; corrigir o modo `perguntar`; tirar datas, caminhos e exemplos do autor; descrição neutra da `tarefas`.
5. **Criação:** descoberta primeiro (conectores, sistema, git), depois uma ou duas perguntas de confirmação,
   semeando `config/fontes`, `config/projetos` e os campos novos.
6. **Verificar:** instalação limpa como uma pessoa fictícia `en-US`, sem Granola, sem git, com um gestor tipo Asana;
   no macOS e, se possível, Windows e Linux: `/cortex:quadro-tarefas` → `/cortex:bom-dia` → `/cortex:boa-noite`.
   Revisão cruzada pelo Codex antes de publicar a versão.

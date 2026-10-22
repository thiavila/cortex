# Gestor: genérico (qualquer ferramenta com conector)

Receita para `config/gestor.tipo = "generico"`: Asana, ClickUp, GitHub Issues, GitLab, Azure DevOps, Trello, Todoist,
Monday, Basecamp, Shortcut… qualquer gestor de tarefas que tenha conector ligado na sessão. Regras gerais:
`<skills>/tarefas/SCHEMA.md` § `config/gestor` e § Quadro × gestor. A diferença para Linear/Jira/Notion é que a receita
não está num arquivo: ela é **descoberta pelo conector** na configuração e guardada em `config/gestor.receita`.

## Descobrir (no `/quadro-tarefas gestor` ou na criação do quadro)
1. **Conector:** as tools da sessão cujo nome traz o serviço (`asana`, `clickup`, `github`, `gitlab`, `azure`,
   `trello`, `todoist`, `monday`…). Carregar as adiadas com `ToolSearch`. Sem conector ligado → o gestor fica
   `pendente: true` e a pessoa é avisada de que precisa ligar o conector (`/mcp` ou as configurações do app).
2. **Quem é a pessoa:** a tool de "me"/"whoami"/"current user" → `receita.eu` (id ou login). Serve para o filtro
   "atribuído a mim".
3. **Onde ler e escrever:** listar workspaces/projetos/repositórios/quadros visíveis; mais de um → perguntar qual (ou
   quais, para leitura) numa pergunta só; gravar os ids em `config`.
4. **Status:** ler os status/seções/colunas/estados do lugar escolhido (no GitHub Issues: `open`/`closed` e as labels
   de estado, se houver) e propor o `mapa_status` (sugestão abaixo).
5. **Montar a `receita`**, um item por operação, cada um com a tool exata e os argumentos (com `<placeholders>` para
   o que muda):
   ```json
   { "conector": "<prefixo das tools>", "eu": "<id/login>",
     "ler_abertas": "<tool> {assignee: <eu>, status: aberto, projeto: <id>} — paginar por <campo>",
     "ler_mudadas": "<tool> {…, updated_since: <início da janela>}",
     "ler_um": "<tool> {id}",
     "buscar": "<tool> {query: <palavras>, todos os status}",
     "criar": "<tool> {projeto, título, descrição, responsável: <eu>, …}",
     "mudar_status": "<tool> {id, status|seção|coluna|state}",
     "comentar": "<tool> {id, texto}",
     "link": "https://…/<ID>",
     "status": ["<nomes dos status lidos>"] }
   ```
   O que o conector não oferece (ex.: sem comentário) fica `null`: a operação não é proposta.
6. **Chave dos cards:** `prefixo_chave` = nome curto do serviço (`asana`, `clickup`, `gh`, `ado`, `trello`,
   `todoist`); o `<ID>` é o identificador estável do item (no GitHub, `dono/repo#123`).
7. **Leitura:** `config/gestor.leitura.filtro` (padrão `atribuido_a_mim`; outros: `criado_por_mim`, `seguindo`,
   `projeto`, `consulta`) e o detalhe em `leitura.texto`.
8. **Testar antes de gravar:** rodar `ler_abertas` uma vez e mostrar quantos itens vieram e 2–3 títulos. Só então
   gravar `config/gestor` com `pendente: false`.

**Obrigatório:** `receita.conector`, `receita.ler_abertas` e `mapa_status`. Faltando → `pendente` (sem sincronizar nem
escrever). Faltando só `receita.criar` → lê e edita, mas não cria.

## Ler e escrever
Seguir a `receita` gravada, com os mesmos cuidados das receitas fixas:
- `fields`/campos enxutos sempre que o conector permitir; paginar até o fim.
- Buscar antes de criar, em **todos os status**: mesmo item aberto (ligar) · mesmo item fechado (ligar e fechar o
  card) · nenhum (trabalho novo).
- Mudar status só para um nome que existe em `receita.status`; se a ferramenta usa transições (como o Jira), descobrir
  a transição antes e nunca adivinhar o id.
- Nunca criar projeto, seção, coluna, label ou campo novo sem a pessoa pedir.

## Status
Sugestão de `mapa_status`, pelo sentido dos nomes lidos: algo como "Inbox"/"Triage"/"New" → `entrada`;
"To do"/"Backlog"/"Not started" → `a_fazer`; "In progress"/"Doing" → `fazendo`; "Blocked"/"Waiting"/"In review" →
`esperando` (senão `null`); "Done"/"Completed"/"Closed" → `feito`; "Canceled"/"Won't do" → `descartada` (senão o mesmo
de `feito`, com comentário). Ferramentas só aberto/fechado (GitHub Issues, Todoist): `fazendo`/`a_fazer`/`entrada` →
aberto, `feito`/`descartada` → fechado (no GitHub, `state_reason: completed | not_planned`).

## Cuidados
- Comentário de fechamento curto, no idioma da pessoa, sem citar o Claude: "Concluído em <data>: <o que foi entregue>".
- A receita guarda nomes de tools e ids, nunca token.

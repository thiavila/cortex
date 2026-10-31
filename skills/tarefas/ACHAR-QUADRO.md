# Achar o quadro desta conta

`<skills>` = a pasta onde estão as skills do quadro (a mãe da pasta `tarefas`).

Procedimento único, usado por `tarefas`, `quadro-tarefas`, `tarefas-io`, `fechar`, `/bom-dia` e `/boa-noite`.

## Antes da descoberta de artifacts

Resolver primeiro a seleção descrita em `LOCAL.md`. Em backend `local`, ler apenas o perfil explicitamente
selecionado e validar o UUID com o runtime; esse é o quadro. Não listar artifacts nem usar `mine`, URLs do
Claude ou `quadros.py` para descobrir um quadro local. Sem seleção fora do Claude, executar o setup antes
de checar capacidades. As regras abaixo são somente do backend `artifact` e do Claude legado.

**Princípio:** cada pessoa tem um quadro por conta do Claude. O quadro é um artefato da própria conta, e
só a conta dona o acha na sua lista de artefatos (`Artifact list`, "mine"). Nada de escolher pelo nome do
app, pela pasta ou por `CLAUDE_CONFIG_DIR`. O arquivo local é só um atalho para não listar toda vez.

**Ser dono ≠ ter acesso.** Um quadro compartilhado por outra pessoa também responde ao `ArtifactData`.
Por isso a prova de que o quadro é desta conta é aparecer em "mine", e o atalho local só guarda quadros
que já passaram por essa prova.

## 0. Capacidades desta sessão
O Cortex roda no app desktop do Claude (aba Code) e no Claude Code de terminal (CLI), no macOS, Windows e Linux. Algumas
ferramentas só existem no app. Antes de usar uma, ver se ela está entre as tools da sessão (carregada ou adiada; as
adiadas se carregam com `ToolSearch`). **Faltou uma → seguir pelo caminho da direita, sem quebrar e sem comentar**,
a não ser que a falta mude o resultado para a pessoa (aí uma linha no fim).

| Ferramenta | Sem ela |
|---|---|
| `ArtifactData`, `Artifact` | neste backend artifact, parar e explicar que são necessárias ferramentas de artifacts do Claude; para outro agente, primeiro seguir o setup de `LOCAL.md`, sem trocar backend automaticamente |
| `get_session` (`"self"`) | a conversa vem do aviso do hook: `sessao=`, `cwd=`, `entrada=`; no CLI a chave é `conversa:cli:<sessao>` e o título é a primeira mensagem. Sem aviso do hook: `cwd` = a pasta atual, conversa sem chave (não ligar) |
| `set_session_title` | não renomear nada (nem a própria conversa, nem propor `✏️` no `/boa-noite`) |
| `list_sessions`, `list_events` | conversas pelos transcritos locais: `sh <skills>/tarefas/py <skills>/boa-noite/conversas.py extrair --backend transcritos …` (o `/boa-noite` já usa o script; o `/bom-dia` lê o manifesto dele em vez de `list_events`) |
| `archive_session` | não arquivar: listar no relatório as conversas que podem ser fechadas |
| `send_message` | o recado vai para o `historico` do card e para a resposta, com o link/comando para retomar a conversa |
| `spawn_task` | tarefa sugerida vira texto: título curto + o prompt pronto para a pessoa colar numa conversa nova |
| `list_scheduled_tasks`, `list_task_runs` | pular as rotinas |
| `AskUserQuestion` | perguntar em texto, com as opções numeradas, e esperar a resposta |
| `Agent` (subagentes) | resumir as conversas na própria sessão, em lotes menores |

**Python:** sempre `sh <skills>/tarefas/py <script> …` (acha `python3`, `python` ou `py -3`). Sem Python 3.8+, os passos
que usam script ficam de fora e a skill diz em uma linha o que instalar.

**Abrir um link no navegador:** `open <url>` (macOS), `xdg-open <url>` (Linux), `start "" <url>` (Windows/Git Bash:
`cmd //c start "" <url>`); falhou ou sem shell → só mostrar o link.

## Busca rápida (primeira mensagem do hook e escritas ao longo do dia)
1. `sh <skills>/tarefas/py <skills>/tarefas/quadros.py listar` → URLs já confirmadas nesta máquina (de qualquer conta
   da pessoa). Para cada uma, em paralelo, a leitura que o chamador já precisa (em geral `get config/preferencias`;
   na primeira mensagem também `get indice/ativos`). As que voltam "sem acesso" são de outra conta da pessoa:
   é esperado e não se comenta.
2. **Exatamente uma respondeu** → é esta. Fim.
3. **Nenhuma, ou mais de uma** → busca completa.

## Busca completa (uma vez por `/bom-dia`, `/boa-noite` e `/quadro-tarefas`, e quando a rápida não decide)
1. `Artifact action: "list"` (`scope: "mine"`, `limit: 50`). O título não decide (a pessoa pode ter renomeado, e o
   idioma muda): o que marca o quadro é `config/schema.formato == "quadro-tarefas"` (quadros antigos, sem `formato`:
   `versao` + `escopo` presentes). Primeiro, `get config/schema` em paralelo nos títulos que começam com `Cortex`,
   `Tarefas` ou `Tasks` e nos do atalho local; nenhum quadro entre eles → o mesmo `get` em todos os da lista.
2. Junta com as URLs do atalho que responderam e **estão** em "mine". Uma que responde mas não está em
   "mine" é compartilhada por outra pessoa: não é deste quadro e não se escreve nela automaticamente.
3. **Um quadro** → é este. **Dois ou mais** → vale o único com `config/preferencias.principal: true`. Nenhum ou
   mais de um principal → perguntar UMA vez, numa pergunta só: qual é o principal e o que fazer com os outros
   (apagar, que é o normal para quadro antigo ou provisório, ou manter). Gravar `principal: true` no escolhido e
   `false` nos mantidos; os que a pessoa mandar apagar vão para `Artifact action: "delete"` (o app pede a
   confirmação dela) e saem do atalho (`quadros.py esquecer`). Depois disso a pergunta não volta.
4. `sh <skills>/tarefas/py <skills>/tarefas/quadros.py lembrar --url <url> --titulo "<título>"` para cada quadro da
   conta (inclusive os não principais: assim a busca rápida enxerga o empate da próxima vez). URL do atalho que
   não responde em nenhuma conta há muito tempo pode ser esquecida (`esquecer`).
5. **Nenhum quadro** → dizer em uma linha que esta conta ainda não tem quadro e oferecer `/quadro-tarefas`.
   Se o usuário colar um link: testar com `get config/schema`; se estiver em "mine", `lembrar`; se não
   estiver (quadro de outra pessoa), só ler, e escrever apenas no que o usuário pedir explicitamente.
   A lista traz no máximo 50 artefatos: se a pessoa disser que tem quadro e ele não apareceu, pedir o link.
6. `config/schema` sem `formato`, ou `versao` abaixo da atual (4) → na primeira escrita da rodada, as migrações de
   `<skills>/tarefas/MIGRACOES.md`, em ordem.

## Escopo
`escopo` = `config/preferencias.escopo` do quadro achado. Nunca é critério para escolher o quadro.
As ferramentas de cada escopo (agenda, reuniões, chat, código, conversas) não ficam nas skills: vêm de `config/fontes`
no banco do quadro (`SCHEMA.md` § `config/fontes`); sem ele, dos conectores ligados na sessão.
O gestor de tarefas é tipado à parte, em `config/gestor` (`SCHEMA.md` § `config/gestor`).

## Regras
- Escrever só no quadro escolhido acima nesta sessão. Nunca reaproveitar URL de outra sessão sem testar.
- O atalho local só acelera a busca. Limite aceito: se a única URL que responde for de um quadro de outra conta
  compartilhado com esta, a busca rápida o usa até a próxima busca completa (`/bom-dia`/`/boa-noite`), que acha o
  quadro desta conta, faz a rápida ver dois e desempatar pelo "mine".
- Não citar no chat as tentativas que falharam; só o resultado (ou a falta de quadro).

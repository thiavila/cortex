# Achar o quadro desta conta

`<skills>` = a pasta onde estão as skills do quadro (a mãe da pasta `tarefas`).

Procedimento único, usado por `tarefas`, `quadro-tarefas`, `tarefas-io`, `/bom-dia` e `/boa-noite`.

**Princípio:** cada pessoa tem um quadro por conta do Claude. O quadro é um artefato da própria conta, e
só a conta dona o acha na sua lista de artefatos (`Artifact list`, "mine"). Nada de escolher pelo nome do
app, pela pasta ou por `CLAUDE_CONFIG_DIR`. O arquivo local é só um atalho para não listar toda vez.

**Ser dono ≠ ter acesso.** Um quadro compartilhado por outra pessoa também responde ao `ArtifactData`.
Por isso a prova de que o quadro é desta conta é aparecer em "mine", e o atalho local só guarda quadros
que já passaram por essa prova.

## Busca rápida (primeira mensagem do hook e escritas ao longo do dia)
0. **Sem a ferramenta `ArtifactData`** (Codex, Gemini, CLI sem artefatos): parar e dizer que o quadro só é
   acessível onde o Claude tem artefatos (app do Claude, claude.ai/code).
1. `python3 <skills>/tarefas/quadros.py listar` → URLs já confirmadas nesta máquina (de qualquer conta
   da pessoa). Para cada uma, em paralelo, a leitura que o chamador já precisa (em geral `get config/preferencias`;
   na primeira mensagem também `get indice/ativos`). As que voltam "sem acesso" são de outra conta da pessoa:
   é esperado e não se comenta.
2. **Exatamente uma respondeu** → é esta. Fim.
3. **Nenhuma, ou mais de uma** → busca completa.

## Busca completa (uma vez por `/bom-dia`, `/boa-noite` e `/quadro-tarefas`, e quando a rápida não decide)
1. `Artifact action: "list"` (`scope: "mine"`, `limit: 50`). Candidatos: títulos que começam com `Tarefas`.
   Em paralelo, `get config/schema` em cada um. É quadro quando `formato == "quadro-tarefas"` (quadros antigos,
   sem `formato`: `versao` + `escopo` presentes).
2. Junta com as URLs do atalho que responderam e **estão** em "mine". Uma que responde mas não está em
   "mine" é compartilhada por outra pessoa: não é deste quadro e não se escreve nela automaticamente.
3. **Um quadro** → é este. **Dois ou mais** → vale o único com `config/preferencias.principal: true`. Nenhum ou
   mais de um principal → perguntar UMA vez, numa pergunta só: qual é o principal e o que fazer com os outros
   (apagar, que é o normal para quadro antigo ou provisório, ou manter). Gravar `principal: true` no escolhido e
   `false` nos mantidos; os que a pessoa mandar apagar vão para `Artifact action: "delete"` (o app pede a
   confirmação dela) e saem do atalho (`quadros.py esquecer`). Depois disso a pergunta não volta.
4. `python3 <skills>/tarefas/quadros.py lembrar --url <url> --titulo "<título>"` para cada quadro da
   conta (inclusive os não principais: assim a busca rápida enxerga o empate da próxima vez). URL do atalho que
   não responde em nenhuma conta há muito tempo pode ser esquecida (`esquecer`).
5. **Nenhum quadro** → dizer em uma linha que esta conta ainda não tem quadro e oferecer `/quadro-tarefas`.
   Se o usuário colar um link: testar com `get config/schema`; se estiver em "mine", `lembrar`; se não
   estiver (quadro de outra pessoa), só ler, e escrever apenas no que o usuário pedir explicitamente.
   A lista traz no máximo 50 artefatos: se a pessoa disser que tem quadro e ele não apareceu, pedir o link.
6. Quadro antigo sem `formato` → na primeira escrita da sessão, `update` em `config/schema` com
   `formato: "quadro-tarefas"` (com `if_version`). `versao` abaixo da atual (3) → na mesma escrita, as migrações de
   `SCHEMA.md` § Migrações, em ordem (v1 → v2: `config/gestor` a partir de `export`; v2 → v3: cards em vários projetos).

## Escopo
`escopo` = `config/preferencias.escopo` do quadro achado. Nunca é critério para escolher o quadro.
As fontes de cada escopo (agendas, reuniões, bases próprias) não ficam nas skills: vêm de `config/fontes` no
banco do quadro (ou, sem ele, de `~/.claude/tarefas/fontes-<escopo>.md`, ou de um padrão genérico pelos conectores ligados).
O gestor de tarefas (Linear, Jira, Notion…) é tipado à parte, em `config/gestor` (`SCHEMA.md` § `config/gestor`).

## Regras
- Escrever só no quadro escolhido acima nesta sessão. Nunca reaproveitar URL de outra sessão sem testar.
- O atalho local só acelera a busca. Limite aceito: se a única URL que responde for de um quadro de outra conta
  compartilhado com esta, a busca rápida o usa até a próxima busca completa (`/bom-dia`/`/boa-noite`), que acha o
  quadro desta conta, faz a rápida ver dois e desempatar pelo "mine".
- Não citar no chat as tentativas que falharam; só o resultado (ou a falta de quadro).

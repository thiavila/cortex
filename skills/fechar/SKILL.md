---
name: fechar
description: >
  Fecha a conversa atual quando o trabalho dela terminou: atualiza o card do quadro de tarefas (status, resumo,
  links, histórico), registra no diário do dia e arquiva a própria conversa (no app desktop), para a barra lateral
  só mostrar o que está vivo. Pedido pelo usuário ("/fechar", "pode fechar", "fecha essa", "encerra a conversa", "valeu, era isso,
  fecha") → confere se falta algo e fecha. Sugerido pelo agente (a entrega principal acabou: PR mergeado, deploy
  feito, rotina criada, documento aprovado) → pergunta antes ao usuário se faz sentido fechar. Não roda em rotina
  agendada nem com trabalho pendente arriscado. (English: "close this conversation", "we're done here, close it".)
user_invocable: true
argument-hint: "(nenhum) | manter — só atualiza o card, sem arquivar"
---

# fechar — fechar a conversa que terminou

## Runtime primeiro

Antes dos passos abaixo, ler `<skills>/tarefas/LOCAL.md` e resolver a seleção explícita do perfil.
**Backend local:** seguir o transporte, a identidade de quadro/conversa e as exceções dessa referência;
as menções abaixo a `ArtifactData`, conta do Claude, índice manual e ferramentas de sessão são do adapter
Claude e devem ser traduzidas. As regras de tarefas e as autorizações do usuário continuam valendo.
**Backend artifact explicitamente selecionado, ou legado confirmado por `routing: unconfigured` (nenhuma regra ativa para este host):** manter o fluxo abaixo. Sem seleção em outro
agente, oferecer o setup de `quadro-tarefas`; não criar nem escolher um quadro automaticamente.


Objetivo: a conversa que acabou sai da frente **sem perder nada**. O card guarda o que aconteceu e o link da conversa
(arquivada dá para reabrir; no CLI, o comando `claude --resume`); o `/boa-noite` encontra o fechamento no diário do dia.

`<skills>` = a pasta-mãe do Base directory desta skill. Contrato: `<skills>/tarefas/SCHEMA.md`.
Quadro desta conta: `<skills>/tarefas/ACHAR-QUADRO.md` (busca rápida; o § 0 diz o que fazer sem as ferramentas do
app desktop). Idioma das linhas e do histórico: `config/preferencias.idioma`.

## Dois jeitos de começar
**1. O usuário pediu** (`/fechar`, "pode fechar", "fecha essa", "encerra a conversa"): só conferir as travas do
passo 2. Nada faltando → fechar direto, sem perguntar. Algo faltando → dizer o quê em uma linha e perguntar se fecha
mesmo assim ou resolve antes. Pedido explícito vale até para conversa protegida (`titulo_conversa.manter`).

**2. O agente percebeu** que a entrega principal ficou pronta (PR mergeado, deploy concluído, rotina/skill criada e
testada, documento entregue e aprovado, dúvida respondida e o usuário satisfeito): **perguntar antes**, com
AskUserQuestion, uma pergunta só:
> "A entrega desta conversa parece concluída (<resultado em meia linha>). Faz sentido fechar?"
> opções: `Fechar` (atualiza o card e arquiva) · `Só atualizar o card` (sem arquivar) · `Manter aberta`
Seguir conforme a resposta. `Manter aberta` → não sugerir de novo nesta conversa, a menos que ela entregue outra coisa.

O agente **não sugere** quando: `config/preferencias.fechar.modo` é `desligado`; a conversa está em
`titulo_conversa.manter`; é rotina agendada, subagente, `/bom-dia`, `/boa-noite` ou acompanhamento contínuo (um
monitor, um agente que fica rodando); só uma etapa terminou e o trabalho segue; o usuário acabou de pedir outra coisa.

## Passos
1. **Contexto:** a conversa (`get_session "self"`: sessionId, título, cwd, branch; sem a tool, a do aviso do hook,
   `conversa:cli:<id>`, e a pasta atual), e em paralelo `get config/preferencias` e `get indice/ativos` no quadro.
   Achar o card pela chave da conversa; sem card, criar um (regras da skill `tarefas`) já com o resultado.
2. **Travas** (qualquer uma → atualizar o card, NÃO arquivar, dizer o motivo em uma linha):
   - só com `config/preferencias.codigo.usa_git` e a pasta num repositório git: mudança pendente no `git status` (fora
     os caminhos de `codigo.ruido`), arquivo novo fora do git numa worktree que não foi copiado (com
     `codigo.copiar_fora_do_git`, e só depois do pedido ou do sim para fechar, copiar para o mesmo caminho no checkout
     principal sem sobrescrever; senão, avisar),
     ou commit sem push (`git log <remoto>/<base>..HEAD`, com `codigo.remoto` e `codigo.branch_base`; base `null` = a
     branch padrão do remoto);
   - pedido de mudança (PR/MR) aberto e não mergeado, quando houver (o card vai para `esperando`, com o link em `links`);
   - tarefa em segundo plano ou agente ainda rodando nesta conversa;
   - pergunta ao usuário sem resposta que só esta conversa resolve.
3. **Conversa executora** (`papel: "executor"` no card, ou prompt com `Conversa original`): mandar o resultado na
   original por `send_message` (se ainda não mandou; sem a tool, no `historico` do card e na resposta), NÃO mudar `status` nem `resumo` do card (são da original),
   só `historico` (`por: "fechar"`, "executor terminou: …"), `links`/`chaves` e `conversas[].arquivada: true`;
   pular para o passo 4. A linha final vira `✅ Resultado enviado para "<original>". Arquivando esta conversa.`
3a. **Atualizar o card** (`update` com `if_version`):
   - entregue → `status: feito`, `resolucao: concluida`, `concluido_em`; esperando terceiro → `status: esperando` com
     `proximo_passo` dizendo o quê e de quem (a conversa pode ser arquivada mesmo assim: o card guarda o link);
   - `resumo` (1–2 frases do resultado), `historico` com `por: "fechar"` (o que foi feito, decisões, artefatos),
     `links` e `chaves` dos artefatos (PR, commit, documento, URL), `conversas[].arquivada: true` para esta conversa
     (só se ela vai ser arquivada no passo 6);
   - `update` no `indice/ativos` com o status novo.
4. **Diário:** acrescentar em `dias/<hoje>.fechados` (criar o doc com `set` se não existe; senão `update` com
   `if_version`, mandando a lista inteira) `{em, conversa, titulo, tarefa, resumo, status}`. O `/boa-noite` usa isso
   e não precisa resumir esta conversa de novo.
5. **Gestor externo** (o de `config/gestor`): só se o card tem chave do gestor e `escrever.editar` não é `nunca`; com
   `propor_no_boa_noite`, fica para o `/boa-noite`; com `sob_pedido`, só se a pessoa pediu.
6. **Avisar e arquivar:** uma linha, no idioma do quadro — `✅ Card "<título>" → Feito. Arquivando esta conversa.` — e
   então `archive_session` com `session_id: "self"` e `reason` curto (ex.: "PR #12 mergeado"). O app pode pedir a
   aprovação no próprio card; se negar, ou a conversa estiver aberta na tela e o app recusar, dizer que o card já foi
   atualizado e que a conversa pode ser arquivada pela barra lateral. Essa chamada é a última coisa da resposta.
   Não arquivar (só o card e o diário, e a linha diz isso) quando: não há `archive_session` (CLI: a conversa termina
   quando a pessoa sair; o card guarda o `claude --resume`), ou `automacao.arquivar_conversas` é `nao` e a pessoa não
   pediu para arquivar.

Com o argumento `manter`: passos 1–5, sem arquivar.

## Anti-patterns
- ❌ Arquivar com commit sem push, PR aberto, arquivo fora do git ou trabalho ainda rodando (com `codigo.usa_git`).
- ❌ Arquivar sem antes gravar o card e o diário.
- ❌ Fechar por iniciativa própria sem a pergunta; ou perguntar no meio do trabalho, só porque uma etapa terminou.
- ❌ Arquivar outra conversa: esta skill só fecha a própria (as outras são do `/boa-noite`).

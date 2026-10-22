---
name: tarefas-io
description: >
  Exporta e importa o quadro de tarefas (artefato com banco) de/para outro lugar: pacote JSON completo,
  CSV, Markdown, ou outro task manager (o gestor de config/gestor — Linear, Jira, Notion — ou Todoist, planilha),
  casando tarefas pelas chaves externas para não duplicar. Use quando pedirem "exporta minhas tarefas",
  "backup do quadro", "importa do Linear/Jira/Notion/Todoist/CSV", "manda o quadro pro <ferramenta>",
  "migra o quadro pra outra conta", "tarefas-io".
user_invocable: true
argument-hint: "export [json|csv|md|gestor|<destino>] | import <arquivo|gestor|linear|jira|notion|todoist|csv>"
---

# tarefas-io — tirar e colocar tarefas

`<skills>` = a pasta-mãe do Base directory desta skill (vale em `~/.claude/skills` e dentro do plugin).

Script: `<skills>/tarefas/io.py` (export e plano de import). Contrato: `<skills>/tarefas/SCHEMA.md`.
Quadro: o desta conta, por `<skills>/tarefas/ACHAR-QUADRO.md`. Pacotes ficam em `~/.claude/tarefas-exports/`
(fora da pasta de skills, que é sincronizada com outros agentes).

## Export
1. Baixar com `ArtifactData list` + `out_dir: <scratchpad>/exp-<escopo>` as coleções `tasks`, `dias`,
   `arquivo` e `config` (`query.limit: 1000`; se vier `next_cursor`, continuar).
2. `python3 <skills>/tarefas/io.py export --dir <scratchpad>/exp-<escopo> --escopo <escopo> --out ~/.claude/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json [--csv … --md …]`
3. **Para outro task manager** (padrão: o gestor de `config/gestor`; sem ele, `config/preferencias.export.destino`,
   obsoleto; ou o que o usuário disser):
   - Gestor configurado: receita `<skills>/tarefas/referencias/gestores/<tipo>.md`, `mapa_status`, `regras` e a regra
     da relação (`SCHEMA.md` § Quadro × gestor): só cards de nível de cima (sem `pai`, sem tag `gestor:fora`) vão; com
     chave do gestor → editar; sem chave (nem de `legado`) → buscar antes em todos os status e ligar se já existir,
     senão criar; só com chave de `legado` → só ligar se achar claramente. Cada operação respeita o seu modo:
     `escrever.criar: "nunca"` → não cria; `escrever.editar: "nunca"` → não edita; o que ficar de fora vai no CSV.
     Gestor pendente → não escrever (completar com `/quadro-tarefas gestor`).
   - Outro destino: mapa de status proposto, perguntado e usado só nesta exportação (se virar o gestor da pessoa,
     gravar em `config/gestor`).
   - Mostrar a prévia (quantos criados/editados/ligados; tarefas com chave do destino são atualizadas, não recriadas).
   - Só depois do ok, escrever pelo conector (receita do gestor; demais pelo conector disponível ou CSV para o usuário importar).
   - Gravar a chave criada de volta na tarefa (`chaves: [..., "linear:ABC-123"]`) para o próximo export atualizar.
4. Responder com o caminho dos arquivos e as contagens.

## Import
1. **Converter para o formato v1** (lista de tarefas ou pacote `{tasks: {...}}`):
   - pacote deste sistema → já está;
   - Linear, Jira, Notion → a leitura da receita (`<skills>/tarefas/referencias/gestores/<tipo>.md`), com
     `chaves: ["<prefixo>:<ID>"]`, `fonte: {tipo, ref}` e link para o item; status pela receita/`mapa_status`;
   - Todoist/CSV → mapear colunas (título, status, prazo, projeto, etiquetas → `tags`). No CSV deste sistema,
     `projeto` = o principal e `projetos` = todos, como lista JSON (`["Site", "App"]`; o `io.py` aceita
     esse texto direto). Texto que não é lista JSON vale como um projeto só.
   Status desconhecido vira `entrada`. Tags no formato `tipo:valor` sem acento. Prefixo de `legado` não se importa sem
   a pessoa pedir.
2. Baixar o índice atual (`ArtifactData get indice/ativos` com `out_dir`) e rodar
   `python3 <skills>/tarefas/io.py plan --entrada <arquivo> --indice <indice.json> --saida <scratchpad>/plan [--com-config]`.
3. Mostrar a `preview.md` resumida (novas × atualizadas × conflitos) e **esperar o ok**.
4. **Tarefas novas** (`op: set`): vão como estão, no `batch`. Antes, conferir com `get` que o id ainda está livre.
5. **Tarefas existentes** (`op: update`, `"if_version": "PREENCHER"`): o arquivo NÃO vai direto. Para cada uma,
   `get` da tarefa atual (versão + dados) e montar o `update` com: os escalares do arquivo; `chaves`, `tags` e
   `links` = união do atual com `_unir`; `projetos` = os atuais (o principal continua primeiro) + os novos de `_unir`,
   com `projeto` = o primeiro e uma tag `projeto:<slug>` para cada um; `historico` = `[{em, texto: _historico, por: "io"}] + atual` (até 50);
   `atualizado_em`; `if_version` = versão lida. Conversas, contexto, resumo e ligações locais não são tocados.
   Conflito de versão → reler e remontar, nunca forçar.
6. Mandar os lotes em `ArtifactData batch` e, no fim, um `update` em `indice/ativos` com o conteúdo de
   `indice-merge.json` (`data: {itens: …, atualizado_em}` + `if_version`). Para as tarefas **atualizadas**, a entrada
   do índice é refeita a partir do card final (depois da união): `p` = `projeto`, `ps` = `projetos`, `tags`, `k` =
   `chaves`, `s`, `t`, `pai`, `u`. O `indice-merge.json` traz só uma prévia dessa união.
   `--com-config` (dias/arquivo/config) **substitui** documentos: só em quadro novo, logo depois do `quadro-tarefas`.
7. Conferir com um `list` de `tasks` e responder com as contagens (e os conflitos que ficaram de fora).

## Regras
- Sempre prévia antes de escrever, nos dois sentidos.
- Casar pelas `chaves`; nunca duplicar uma tarefa que já tem a mesma chave.
- Pacotes têm dados do usuário: não publicar, não anexar em lugar público, não deixar dentro de `<skills>/`.

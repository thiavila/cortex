---
name: tarefas-io
description: >
  Exporta e importa o quadro de tarefas (artefato com banco) de/para outro lugar: pacote JSON completo,
  CSV, Markdown, ou outro gestor de tarefas (o de config/gestor — Linear, Jira, Notion, Asana, GitHub Issues… —
  ou planilha), casando tarefas pelas chaves externas para não duplicar. Use quando pedirem "exporta minhas
  tarefas", "backup do quadro", "importa do <ferramenta>/CSV", "manda o quadro pro <ferramenta>", "migra o quadro
  pra outra conta", "tarefas-io" (English: "export my board", "import tasks from <tool>").
user_invocable: true
argument-hint: "export [json|csv|md|gestor|<destino>] | import <arquivo|gestor|<ferramenta>|csv>"
---

# tarefas-io — tirar e colocar tarefas

## Runtime primeiro

Antes dos passos abaixo, ler `<skills>/tarefas/LOCAL.md` e resolver a seleção explícita do perfil.
**Backend local:** seguir o transporte, a identidade de quadro/conversa e as exceções dessa referência;
as menções abaixo a `ArtifactData`, conta do Claude, índice manual e ferramentas de sessão são do adapter
Claude e devem ser traduzidas. As regras de tarefas e as autorizações do usuário continuam valendo.
**Backend artifact explicitamente selecionado, ou legado confirmado por `routing: unconfigured` (nenhuma regra ativa para este host):** manter o fluxo abaixo. Sem seleção em outro
agente, oferecer o setup de `quadro-tarefas`; não criar nem escolher um quadro automaticamente.


`<skills>` = a pasta-mãe do Base directory desta skill (vale numa pasta de skills e dentro do plugin).

Script: `sh <skills>/tarefas/py <skills>/tarefas/io.py` (export e plano de import). Contrato: `<skills>/tarefas/SCHEMA.md`.
Quadro: o desta conta, por `<skills>/tarefas/ACHAR-QUADRO.md`. Pacotes ficam em `<dados>/tarefas-exports/`
(`<dados>` = `sh <skills>/tarefas/py <skills>/tarefas/caminhos.py`; fora da pasta de skills).
Textos do export (Markdown, prévia, histórico) no idioma do quadro: `--idioma <config/preferencias.idioma>`.

## Export
1. Baixar com `ArtifactData list` + `out_dir: <scratchpad>/exp-<escopo>` as coleções `tasks`, `dias`,
   `arquivo`, `recorrentes` e `config` (`query.limit: 1000`; se vier `next_cursor`, continuar).
2. `sh <skills>/tarefas/py <skills>/tarefas/io.py export --idioma <idioma> --dir <scratchpad>/exp-<escopo> --escopo <escopo> --out <dados>/tarefas-exports/quadro-tarefas-<escopo>-<AAAA-MM-DD>.json [--csv … --md …]`
3. **Para outro gestor de tarefas** (padrão: o de `config/gestor`; ou o que o usuário disser):
   - Gestor configurado: receita `<skills>/tarefas/referencias/gestores/<tipo>.md` (no `generico`, a `receita` do
     próprio `config/gestor`), `mapa_status`, `regras` e a regra
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
   - gestor com receita (Linear, Jira, Notion, ou o `generico` configurado) → a leitura da receita, com
     `chaves: ["<prefixo>:<ID>"]`, `fonte: {tipo, ref}` e link para o item; status pela receita/`mapa_status`;
   - outra ferramenta/CSV → mapear colunas (título, status, prazo, projeto, etiquetas → `tags`). No CSV deste sistema,
     `projeto` = o principal e `projetos` = todos, como lista JSON (`["Site", "App"]`; o `io.py` aceita
     esse texto direto). Texto que não é lista JSON vale como um projeto só.
   Status desconhecido vira `entrada`. Tags no formato `tipo:valor` sem acento. Prefixo de `legado` não se importa sem
   a pessoa pedir.
2. Baixar o índice atual (`ArtifactData get indice/ativos` com `out_dir`) e rodar
   `sh <skills>/tarefas/py <skills>/tarefas/io.py plan --idioma <idioma> --entrada <arquivo> --indice <indice.json> --saida <scratchpad>/plan [--com-config]`.
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
   `--com-config` (dias/arquivo/recorrentes/config) **substitui** documentos: só em quadro novo, logo depois do `quadro-tarefas`.
7. Conferir com um `list` de `tasks` e responder com as contagens (e os conflitos que ficaram de fora).

## Regras
- Sempre prévia antes de escrever, nos dois sentidos.
- Casar pelas `chaves`; nunca duplicar uma tarefa que já tem a mesma chave.
- Pacotes têm dados do usuário: não publicar, não anexar em lugar público, não deixar dentro de `<skills>/`.

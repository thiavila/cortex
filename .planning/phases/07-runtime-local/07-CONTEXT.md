# Fase 7 — Runtime local e escolha de agentes

## Objetivo
Na primeira configuração, perguntar quais agentes a pessoa usa. Quem usa somente Claude mantém o quadro no artifact da própria conta. Quem usa qualquer outro agente, sozinho ou junto do Claude, usa uma réplica local do quadro, com os mesmos dados acessíveis aos agentes e à interface.

## Decisões da conversa
- **D-01 — Só Claude:** preservar Artifact/ArtifactData, a descoberta por propriedade da conta e os quadros existentes.
- **D-02 — Qualquer outro agente:** Codex, Gemini ou outro agente seleciona o backend local, inclusive quando Claude também está selecionado. O conjunto de agentes é aberto, sem uma lista fechada de fornecedores.
- **D-03 — Experiência compartilhada:** reutilizar o quadro interativo existente e suas regras; agentes e página acessam uma única persistência local, com tarefas, histórico, diário, recorrentes e preferências.
- **D-04 — Escolha explícita e estável:** perguntar no primeiro setup, lembrar a resposta, permitir reconfiguração explícita e não inferir ou trocar o backend por detectar ferramentas instaladas.
- **D-05 — Sem hospedagem obrigatória:** servidor de loopback e SQLite no computador. Não implementar modo Pages nem exigir serviço na internet.
- **D-06 — Preservação:** não migrar automaticamente quadros existentes; troca de modo oferece export/import com prévia, confirmação e validação, preservando origem, histórico e vínculos.

## Implementação acordada pelo orquestrador
- A pergunta acontece na primeira execução do setup/skill, apresentada como parte da instalação guiada; instalação não interativa não inventa resposta.
- Python da biblioteca padrão acompanha a base existente; não instalar dependências ou software global só para esta implementação.
- CLI e MCP stdio compartilham o mesmo dispatcher/SQLite. O servidor HTTP serve o mesmo HTML/CSS do quadro e uma ponte de dados local.
- A identidade primária é um descritor de quadro com backend e ID. URL do artifact é detalhe do backend Claude; caminho do banco é detalhe do backend local. Escopo/empresa não é deduzido do app nem do diretório de projeto.
- Estado local separado da pasta de plugins, com raiz própria do Cortex e seleção explícita de quadro/perfil. A raiz local não herda automaticamente CLAUDE_CONFIG_DIR.
- Usar ferramentas de conversas disponíveis em cada host; onde não houver capacidade, declarar a limitação, sem inventar APIs ou ler transcritos de outro fornecedor.
- Nenhuma instalação na conta pessoal, alteração de quadros reais, upload ou deploy faz parte dos testes.

## Descoberta e limites
- Base inspecionada: `614c337`, esquema de documentos 4 e plugin 0.3.1.
- A página atual usa `window.claude.use("db")` e `use("user")`; o contrato usa versões para escrita. A UI depende de doc/collection, get/set/update/delete e onSnapshot.
- O export existente inclui tasks, dias, arquivo, config e recorrentes. Pode ser usado como pacote de migração sem buscar dados privados durante desenvolvimento.
- As seis skills atualmente referenciam ArtifactData e ferramentas de sessão do Claude. A adaptação precisa atingir todas, não apenas quadro-tarefas.
- A documentação oficial de plugins consultada pelo orquestrador suporta pacote de skills e MCP local. Confirmar metadados pelo formato atual durante o empacotamento; não pressupor que instalação registre automaticamente ferramentas em todas as sessões.

## Organização
O quick task `261028-vni-cortex-onboarding-claude-only-artifact-o` foi promovido para a fase 7 por abranger runtime, interface e portabilidade. Isso é divisão interna da implementação já autorizada. Executar os planos sequencialmente na worktree dedicada; não alterar o checkout principal ou o histórico das fases 1–6.

## Fora do escopo
Hospedagem remota, sincronização entre computadores, publicação em diretórios públicos, conectores novos de gestores e modo Pages. A capacidade de usar outra ferramenta de agente não implica paridade de gerenciamento de conversas quando o host não expõe essa capacidade.

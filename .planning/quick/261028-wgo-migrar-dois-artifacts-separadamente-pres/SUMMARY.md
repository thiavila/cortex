---
status: complete
review: pending
---
# Migração e identidade dos artifacts

Escopo confirmado: dois quadros separados; reproduzir o visual existente, sem redesign genérico.

Exportação ao vivo pela interface autenticada do navegador, usando somente leituras do SDK do quadro. Coleções completas abaixo do limite de 1000 documentos em cada consulta. Backups originais e dados migrados mantidos fora do repositório, em diretório privado do usuário. Nenhuma exclusão/publicação/escrita direta no artifact de origem.

Achados reais: o runtime ignorava fontes do tema e o reset de margem injetado pelo host Claude. Também tratava vínculos de conversa/PR/repo/branch/GSD como IDs exclusivos, rejeitando cards distintos que compartilham evidências.

Correções: preservar Google Fonts somente com opt-in explícito do tema; CSP limitada aos domínios de CSS/fontes, dados continuam same-origin; reset e viewport no HTML local; título visual opcional sem renomear preferências; vínculos de contexto compartilháveis, mantendo a exclusividade de outras identidades externas. Regressões cobertas.

Dados: conferência estrutural exata de tasks/dias/arquivo/recorrentes entre backup e SQLite antes e depois de abrir a UI. Configurações/tema preservados; compatibilidade do quadro v3 preparada numa cópia (locale/fuso explícitos e schema de origem guardado), sem atualizar o artifact. Cópias persistentes em perfis distintos, originais e backups preservados. Não há sincronização bidirecional automática.

Validação: 31 testes Python + 4 Node passaram. Navegador confirmou tema branco/azul e tipografia condensada do quadro corporativo; tema escuro/verde e tipografia do pessoal. Captura corporativa e cópia pessoal inspecionadas; screenshot do artifact pessoal retornou imagem vazia no MCP, então a comparação desse original usou CSS/DOM/fontes computadas. Não se declara igualdade pixel a pixel. Existem diferenças funcionais de texto da página v4 (atalhos de data e múltiplos projetos) em relação à página antiga.

Revisão Claude ainda pendente: diagnóstico do perfil Pessoal fora do sandbox retornou loggedIn=false; nenhuma nova inferência foi tentada, sem tokens/custo adicionais. PR permanece draft, sem merge/deploy. Para promover: restaurar autenticação, revisar diff completo e validar integração MCP no cliente escolhido.

Servidores de prévia encerrados; dois servidores de uso local mantidos ativos a pedido/contexto de teste do usuário. A aba pode fechar, mas o processo HTTP precisa continuar para usar a página. CLI/MCP leem SQLite independentemente dele.

---
status: complete
review: GO-scoped
---
# Favicons configuráveis

config/tema.favicon referencia PNG/ICO em root/assets, basename validado, resolveparentconfina, limite1MiB, MIME porassinatura, linklocalcomhash para cache e rota sem diretóriolistagem. Sem arquivo/nome de empresa embutido no plugin. Logos originais locais copiados somente para instalação privada, sem transformação.

Teste HTTP passou paraPNG, cachehash, ../rejeitado e SVG rejeitado; todos12 testes test_local.py passaram. Instalação real: dois favicons HTTP200, PNG/ICO, diferenteshashes; reinício manteve origens/autorização e abas Arc recarregadas. Um DOM lido logo após commit retornou antes do parse; verificado novamente após carregamento. Não há alteração de dados de tarefas.

Claude GO para o ajuste por leitura. P3 residual de arquivo especial local e compartilhamento deassets não é limite de segurança entre usuários. Input14/output3481; cache criado11513/lido69285; equivalenteUS$0.175637. PR continua draft pelas pendências gerais anteriores.

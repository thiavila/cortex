---
status: complete
review: GO-scoped
---
# Endereços estáveis para abas fixas

Serviço possui persistent_auth opt-in, com chave aleatória porboard publicada atomicamente via tempfile0600/fsync/link semsobrescrita. Diretório0700; chave0600; leitores nunca veem chave parcial. Browser usa localStorage somente nesse modo, guarda apenas token validado, e fragmentoexpirado pode tentar credencialsalva uma vez após401 (antes de dispatch). CLI mantém autorização efêmera padrão.

Na instalação privada, credenciais atuais foram preservadas e persistent_auth habilitado, mantendo portas jáfixas. Dois reinícios controlados; URLs e tokens idênticos e HTTP200 nos dois quadros. Nas abas reais Arc de cada quadro, rememberAuth=true, credencialsalva=true e sincronizaçãoOK; recarregadas sem fragmento apósrestart. Um lote de navegação MCP retornou WORKER_TIMEOUT/outcomeunknown; não repetido cegamente: abas listadas e verificadas explicitamente uma poruma, confirmando resultado.

Testes: novaaba semfragmento, fragmentoantigo comfallback, tokeninválido não persistido, modoserviçoefêmero epersistente, publicação concorrente16writers/8threads e permissões. Suitefinal registrada na execução. Autorização longa é opt-in e origemloopback deve ser confiável, conforme README. Limpar dados/perfilbrowser exige nova autorização pelo atalho. Links de portas antigas precisam ser substituídos uma vez pelo endereço raiz estável.

Claude revisão somenteleitura GO; recomendação de atomicidade corrigida, rereview específica GO. Agregado: entrada20, saída7031, cache criado18781/lido79392; equivalenteUS$0.3068264. Outros P2 antigos seguem pendentes e PR permanece draft. Dados dos cards não foram alterados diretamente.

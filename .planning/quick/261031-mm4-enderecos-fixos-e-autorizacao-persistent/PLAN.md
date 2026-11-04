# Abas fixas com autorização persistente opt-in

Pedido: salvar abas Arc e reusar URL após reiniciar. Serviço usa portasfixas e pode habilitar persistent_auth, com chave por quadro em browser-auth/ (diretório0700/arquivo0600). CLI continua efêmera. Browser lembra credencial validada em localStorage apenas no modo persistente; fragmento velho tenta credencial salva após401, nunca grava chave inválida. Tokens não entram em HTML servido. Migrar credencial atual do serviço antes do restart para preservar acesso existente; reabrir uma vez no browser, então usar rootURLs estáveis.

Testar restart, novas abas, fragmentos expirados, autenticação; revisar com Claude; habilitar no serviço pessoal e verificar após restart. Não modificar dados ou política de seleção de quadro.

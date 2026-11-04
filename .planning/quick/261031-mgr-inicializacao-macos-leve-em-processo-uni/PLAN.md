# Serviço local leve no macOS

Pedido: iniciar com o computador e consumir pouca memória. Um único processo Python serve os dois quadros via selector bloqueante, sem timer/polling em repouso e sem abrir navegador/Terminal no login. launchd por usuário (inicia ao entrar no macOS, não antes do login). Status privado com URLs temporárias, abertura por atalhos .app. Configuração real fora do repo, código genérico.

Validar dois quadros sintéticos, HTTP autenticado, persistência/restart, credenciais privadas e encerramento. Revisão Claude somente leitura; instalar LaunchAgent, medir RSS/CPU em repouso e verificar leitura dos quadros reais sem escrita. Manter pendências anteriores e PR em draft.

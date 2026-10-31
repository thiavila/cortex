---
status: complete
review: GO-scoped
---
# Serviço leve de login

Implementado service.py opcional e genérico: um processo atende múltiplos quadros com selector bloqueante, sem polling em repouso. URLs temporárias em arquivo atomic0600, nunca em logs. SIGTERM fecha sockets e limpa status do próprio PID. --open abre apenas loopback, sem shell.

Instalação privada macOS: LaunchAgent RunAtLoad/KeepAlive com throttle15s, Nice5 e LowPriorityIO, sem navegador no login; apps de abertura para cada perfil. Nomes/UUIDs/paths privados em configuração fora do repo. Não há alteração nos cards nem deploy remoto. Depende da worktree ativa que contém o runtime.

Verificação: teste real com dois quadros sintéticos, HTTP autenticado, isolamento de cards, restart e persistência; SIGTERM limpo e arquivo0600. launchd print confirmou job running. Duas APIs de quadros reais retornaram200 com UUIDs esperados; apps de abertura executados. RSS em repouso ~26MiB, CPU0,0%, mesmo tempoCPU entre amostras. Consumo do browser separado. Não foi realizado reboot físico.

Claude revisou serviço/teste somente leitura e emitiu GO para esse escopo, sem bloqueadores. Compromissos registrados: single-thread pode reter os dois quadros até5s numa conexão parada; abrir pode falhar se startup passar5s; config inválida reinicia com throttle; open usa credencial transitoriamente em argumentos (mesmo padrão local anterior). Neste uso com2quadros e conta local única, startup medido menor1s; nenhum serviço de rede externa. Outros P2 da revisão geral não são promovidos por esse GO.

Uso peer: Claude Opus5.5; entrada12, saída5688, cache criado15354/lido55499; equivalente estimadoUS$0.2477398. PR continua draft.

# Roteamento por identidade autenticada

Decisão do usuário: política concreta nos bancos; no seu Claude selecionar quadro pela conta Claude autenticada. Plugin agnóstico, opt-in por host; não aplicar essa regra ao Codex nem a outros usuários.

Implementar resolvedor genérico que lê config/roteamento, autenticação real do host, correspondência única e erro sem fallback. Registrar associações reais somente nos bancos privados. Atualizar instruções genéricas e encaminhamento das cópias globais, removendo nomes pessoais delas. Testar contas/organizações, ambiguidade, falha de autenticação e nenhum efeito colateral. Revisar mudança com Claude, atualizar instalação local e verificar resolve na conta autenticada.

Outros achados P2 da revisão anterior continuam fora desta correção de roteamento; PR permanece draft.

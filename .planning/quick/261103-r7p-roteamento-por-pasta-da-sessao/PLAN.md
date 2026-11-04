# Roteamento por pasta da sessão

Problema: a mesma conta do host é usada para escopos diferentes (trabalho e pessoal, nos dois sentidos), e no app desktop `claude auth status` pode reportar o login do config dir do shell em vez da conta do app. Rotear só pela conta manda trabalho para o quadro errado.

Decisão do usuário: a pasta da sessão decide o quadro; fora das pastas cadastradas, perguntar (não chutar pela conta).

Mudança genérica e opt-in: regra de `config/roteamento` aceita `pastas` (caminhos absolutos), sozinha ou junto com `conta`. Regra de pasta que contém a pasta da sessão vence, a mais profunda primeiro, sem consultar o login; depois regras só de conta, como antes. `setup.py resolve` ganha `--cwd`. Documentar em LOCAL.md, SCHEMA.md e README; testes de profundidade, prefixo irmão, symlink, ambiguidade, validação e ausência de chamada de login. Valores reais só nos bancos privados, depois da atualização do plugin.

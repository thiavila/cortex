---
status: complete
date: 2026-11-13
implementation_family: OpenAI
review_family: Anthropic
review_model: claude-opus-5-5
review_verdict: GO (R2)
---

# Codex: roteamento por pasta

O resolvedor só aceitava Claude, mesmo já existindo suporte genérico a regras de pasta. Codex agora aceita regras próprias no config/roteamento, exige --cwd absoluto da sessão e nunca consulta a identidade Claude. Raízes, quadros e contas não são fixados no produto. Usuário autorizou cadastrar regras locais separadas para Pessoal/Avila e Daki, com herança por descendência.

## Mudanças

- routing.py: aceitar codex; exigir cwd explícito absoluto; identidade não implementada falha fechada. Claude preservado.
- setup.py: ajuda do cwd esclarece diferenças entre hosts.
- Hook, LOCAL.md, SCHEMA.md e README: resolver com host real e pasta da sessão; perfil explícito prevalece; sem inferência por login ou outro host.
- Pacote 0.4.4; dois manifests alinhados.
- Quatro testes Codex de regressão: raízes/descendentes, limite entre pastas irmãs, cwd inválido, isolamento de host, contas não suportadas, ambiguidade e ausência de fallback de regra profunda condicionada a conta.

## Verificações e revisão

- 62 testes Python + 13 JavaScript PASS; validação dos manifests e seis skills PASS; diff --check PASS. Testes HTTP exigem permissão loopback normal, bloqueada no sandbox inicial.
- Claude Opus 5.5 Pessoal, R1 GO com melhorias. Incorporados cwd obrigatório, texto de roteamento explícito e teste de regra profunda condicionada a conta. R2 GO, sem bloqueadores. Ajuda do CLI e qualificação textual Claude ajustadas após R2, sem mudança no comportamento revisado.
- Revisão por helper somente leitura: R1 18 tokens novos + 48.242 criação de cache + 263.194 leitura, 6.229 saída; R2 10 novos + 15.986 criação + 41.584 leitura, 3.596 saída. Total de entrada 369.034 (304.778 cache lido), saída 9.825. Custo equivalente de API US$ 0,7713916, pela assinatura local; não implica cobrança adicional de API.
- Tentativa inicial de peer no sandbox não acessou login; repetição com Keychain normal passou. Não houve troca de conta nem novo login.

## Operação e limites

Regras Codex cadastradas via update versionado em ambos os quadros, preservando regras Claude e backup privado. Fora das raízes cadastradas e em ambiguidade continua exigindo escolha. Codex sem --cwd passa a dar invalid_cwd mesmo sem regras ativas: falha fechada deliberada. Regras Codex por conta não são suportadas, precisam de perfil explícito.

Publicação segue CI oficial e instalação pelo gerenciador do plugin. A conclusão da instalação, smoke nas raízes reais e atualização dos encaminhamentos locais ficam no registro de instalação desta quick task.

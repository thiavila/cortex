# Portar os dois quadros preservando identidade

Decisão confirmada: Pessoal e Daki separados; reproduzir as identidades dos artifacts, sem redesign genérico. Reutilizar worktree/PR do runtime local.

1. Verificar acesso aos dois artifacts e obter export atual completo e HTML/CSS/tema, usando interfaces disponíveis. Não usar backup antigo como estado atual. Não alterar dados de origem. Dados privados ficam fora do repositório.
2. Comparar contratos e aparência, corrigir runtime para preservar configurações/tema/fontes e, se necessário, suportar a página específica por quadro. Não trocar os dados reais antes de apresentar a prévia da importação.
3. Validar em cópias temporárias: contagens e hashes de todas as coleções, histórico/conversas, screenshot comparativo, persistência/conflitos. Preparar os dois destinos separados e mostrar para confirmação final quando necessário. Registrar lacunas reais, testes e revisão cruzada.

Execução inline, GSD quick, sem delegação nesta rodada. Revisão Claude anterior pendente por autenticação; não é aprovação para merge.

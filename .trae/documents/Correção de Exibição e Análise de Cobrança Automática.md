# Correção de Exibição, Implementação de Cancelamento e Análise de Cobrança

## Problemas e Solicitações:
1. **Colunas Vazias**: "Plano" e "Validade" não aparecem devido a nomes de campos diferentes entre as coleções do banco.
2. **Cancelamento**: O botão de cancelamento precisa funcionar para todos os tipos de assinatura (Admin e Checkout/Stripe).
3. **Cobrança**: Analisar se a cobrança via Stripe é automática.

## Plano de Ação:

### 1. Backend (superadmin.py)
- **Normalização**: Atualizar `listar_assinaturas` para que as assinaturas de ambas as coleções retornem os campos `plano` e `data_fim` corretamente para o frontend.
- **Cancelamento Robusto**: Atualizar a rota de cancelamento (`/assinaturas/{assinatura_id}/cancelar`) para:
  - Buscar a assinatura tanto em `assinaturas_admin` quanto em `assinaturas` (Checkout).
  - Se for uma assinatura do Stripe, marcar como cancelada no sistema e garantir que o usuário seja rebaixado para trial.

### 2. Análise de Cobrança
- **Conclusão**: A cobrança é **100% automática** via Stripe. 
- O sistema usa assinaturas recorrentes do Stripe. Quando o Stripe cobra o cliente, ele envia um aviso (Webhook) e o sistema renova a validade automaticamente.

## Próximos Passos:
- Aplicar as correções de exibição e a melhoria no cancelamento no backend.
- Verificar se o frontend está passando o ID correto para o cancelamento (já corrigi anteriormente para usar `id || session_id`, mas vou revisar).

Deseja que eu execute estas melhorias?
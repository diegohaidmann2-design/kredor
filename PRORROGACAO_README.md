# 📋 Prorrogação de Empréstimos - GestorCred

## 🎯 Funcionalidade

Sistema de **prorrogação de empréstimos** na modalidade **"Apenas Juros e Capital no Final"** (Bullet Loan / Interest-Only Loan).

---

## 📊 Como Funciona

### **Modalidade "Apenas Juros"**

Nesta modalidade, o cliente:
- **Paga apenas juros** durante os períodos (meses ou semanas)
- **Na última parcela**: paga o capital completo + juros do último período

### **Exemplo Original:**
```
Empréstimo: R$ 10.000,00
Taxa: 10% a.m.
Prazo: 3 meses

Parcela 1: R$ 1.000,00 (apenas juros)
Parcela 2: R$ 1.000,00 (apenas juros)
Parcela 3: R$ 11.000,00 (capital R$ 10.000 + juros R$ 1.000)
```

---

## 🔄 Prorrogação

Quando o cliente chega na **última parcela** (que contém o capital), ele pode **prorrogar** por mais períodos.

### **O que acontece na prorrogação:**

1. **Última parcela** (com capital) → vira parcela de **apenas juros**
2. São criadas **N novas parcelas** de apenas juros
3. Uma **nova última parcela** é criada com capital + juros

### **Exemplo com Prorrogação:**
```
Empréstimo Original:
Parcela 1: R$ 1.000,00 (apenas juros) ✅ Paga
Parcela 2: R$ 1.000,00 (apenas juros) ✅ Paga
Parcela 3: R$ 11.000,00 (capital + juros) ⏳ Chegou o vencimento

Cliente PRORROGA por 2 meses:

Resultado:
Parcela 1: R$ 1.000,00 (apenas juros) ✅ Paga
Parcela 2: R$ 1.000,00 (apenas juros) ✅ Paga
Parcela 3: R$ 1.000,00 (apenas juros) ← MUDOU! Agora só juros
Parcela 4: R$ 1.000,00 (apenas juros) ← NOVA
Parcela 5: R$ 1.000,00 (apenas juros) ← NOVA
Parcela 6: R$ 11.000,00 (capital + juros) ← NOVA ÚLTIMA PARCELA
```

---

## 🔧 Implementação Técnica

### **Backend - Endpoint**

```http
POST /api/emprestimos/{emprestimo_id}/prorrogar
Content-Type: application/json
Authorization: Bearer {token}

{
  "periodos": 2
}
```

### **Validações**

✅ Empréstimo deve ser método "apenas_juros"  
✅ Empréstimo deve estar ativo ou inadimplente  
✅ Última parcela NÃO pode estar paga  
✅ Última parcela deve conter o capital (valor_principal > 0)  
✅ Períodos deve ser maior que zero

### **Lógica de Prorrogação**

1. **Busca última parcela** (que tem valor_principal > 0)
2. **Transforma última parcela** em parcela de apenas juros:
   - `valor_principal = 0`
   - `valor_total = juros_periodo`
   - `saldo_devedor = valor_principal`

3. **Cria N novas parcelas** de apenas juros:
   - Cada uma com `valor_principal = 0`
   - `valor_total = juros_periodo`
   - Datas de vencimento calculadas sequencialmente

4. **Cria nova última parcela**:
   - `valor_principal = valor_emprestimo`
   - `valor_total = valor_emprestimo + juros_periodo`
   - `saldo_devedor = 0`

5. **Atualiza empréstimo**:
   - Novo `prazo_meses` ou `prazo_semanas`
   - `updated_at`

6. **Registra auditoria**

---

## 📱 Interface Frontend

### **Botão de Prorrogação**

Aparece na tela de detalhes do empréstimo quando:
- Método de cálculo é "apenas_juros"
- Empréstimo está ativo
- Existe última parcela pendente com capital

### **Modal de Prorrogação**

- Input: Quantidade de períodos (meses ou semanas)
- Mostra simulação:
  - Parcelas atuais
  - Novas parcelas que serão criadas
  - Nova data da última parcela
  - Total de juros adicionais

---

## 💡 Benefícios

### **Para o Cliente:**
- ✅ Flexibilidade de pagamento
- ✅ Evita inadimplência
- ✅ Mantém histórico de crédito positivo
- ✅ Pode prorrogar múltiplas vezes

### **Para o Credor:**
- ✅ Mantém cliente ativo
- ✅ Recebe juros por mais tempo
- ✅ Reduz inadimplência
- ✅ Histórico completo de prorrogações

---

## 🧪 Testes

### **Teste 1: Prorrogação Simples**
```bash
# Criar empréstimo apenas_juros
# Prorrogar por 2 meses
# Verificar novas parcelas criadas
```

### **Teste 2: Múltiplas Prorrogações**
```bash
# Prorrogar uma vez
# Aguardar chegada da nova última parcela
# Prorrogar novamente
```

### **Teste 3: Validações**
```bash
# Tentar prorrogar empréstimo tabela_price (deve falhar)
# Tentar prorrogar após última parcela paga (deve falhar)
# Tentar prorrogar empréstimo quitado (deve falhar)
```

---

## 📊 Auditoria

Toda prorrogação é registrada na auditoria:

```json
{
  "acao": "PRORROGAR_EMPRESTIMO",
  "entidade": "emprestimos",
  "entidade_id": "uuid-do-emprestimo",
  "detalhes": "Prorrogou empréstimo por 2 mensal(s). Total parcelas: 6",
  "usuario_id": "uuid-do-usuario",
  "usuario_email": "email@example.com",
  "ip": "192.168.1.1",
  "created_at": "2026-04-10T21:00:00Z"
}
```

---

## 🔐 Segurança

- ✅ Requer autenticação JWT
- ✅ Validação de propriedade (usuário deve ser dono do empréstimo)
- ✅ Validação de contexto (multi-tenant)
- ✅ Registro completo em auditoria
- ✅ Validações de negócio (método, status, etc.)

---

## 📈 Métricas

Possíveis métricas para acompanhar:
- Total de prorrogações por mês
- Taxa de prorrogação por cliente
- Média de períodos prorrogados
- Valor total de juros gerados por prorrogações
- Clientes com mais prorrogações

---

## 🚀 Próximas Melhorias

- [ ] Limite máximo de prorrogações por empréstimo
- [ ] Taxa adicional de prorrogação (opcional)
- [ ] Notificação automática via WhatsApp/Email
- [ ] Dashboard de prorrogações
- [ ] Relatório de prorrogações
- [ ] Análise de risco por cliente (baseado em prorrogações)

---

## 📞 Suporte

Para dúvidas ou problemas:
- Documentação completa: `/app/memory/PRD.md`
- Auditoria: Endpoint `/api/auditoria`
- Logs: `/var/log/supervisor/backend.out.log`

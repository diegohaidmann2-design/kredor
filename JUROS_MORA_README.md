# 📊 Sistema de Cálculo Automático de Juros de Mora e Multa

## 🎯 Visão Geral

O sistema agora calcula **automaticamente** juros de mora e multa por atraso nas parcelas vencidas, aplicando as taxas definidas no momento da criação do empréstimo.

---

## ⚙️ Como Funciona

### 1. **Criação do Empréstimo**

Ao criar um empréstimo, você define:

```json
{
  "taxa_multa_atraso": 2.0,        // Multa de 2% aplicada no atraso
  "taxa_juros_mora_diario": 0.033  // Juros de 0.033% ao dia (1% ao mês)
}
```

**Valores padrão:**
- Multa: 2%
- Juros de mora: 0.033% ao dia (equivale a 1% ao mês)

### 2. **Cálculo Automático**

Quando uma parcela vence e entra em atraso, o sistema calcula:

#### **Multa** (aplicada uma única vez)
```
Multa = Valor Devido × (taxa_multa_atraso ÷ 100)
```

#### **Juros de Mora** (aplicado diariamente)
```
Juros Mora = Valor Devido × (taxa_juros_mora_diario ÷ 100) × Dias de Atraso
```

#### **Total Devido**
```
Total = Valor Original + Multa + Juros de Mora
```

---

## 📝 Exemplo Prático

**Parcela:**
- Valor original: R$ 500,00
- Vencimento: 01/03/2026
- Data atual: 11/03/2026 (10 dias de atraso)

**Cálculo:**
1. **Multa (2%)**: R$ 500,00 × 0.02 = **R$ 10,00**
2. **Juros de Mora (0.033% × 10 dias)**: R$ 500,00 × 0.00033 × 10 = **R$ 1,65**
3. **Total a Pagar**: R$ 500,00 + R$ 10,00 + R$ 1,65 = **R$ 511,65**

---

## 🔄 Atualização Automática

### **Quando os valores são recalculados?**

1. **Ao listar parcelas pendentes** (`GET /api/parcelas/pendentes`)
   - Sistema recalcula automaticamente os juros de mora de todas as parcelas

2. **Job automático a cada 6 horas**
   - Scheduler atualiza todas as parcelas atrasadas do sistema
   - Executa em background sem necessidade de intervenção

3. **Ao registrar pagamento**
   - Sistema considera multa + juros de mora no valor total devido

---

## 📡 Endpoints da API

### 1. Listar Parcelas Pendentes
```http
GET /api/parcelas/pendentes
```

**Resposta:** Inclui campos calculados automaticamente
```json
{
  "id": "uuid",
  "numero_parcela": 1,
  "valor_total": 500.00,
  "valor_pago": 0.00,
  "valor_multa": 10.00,        // ✅ Calculado automaticamente
  "valor_juros_mora": 1.65,    // ✅ Calculado automaticamente
  "dias_atraso": 10,            // ✅ Calculado automaticamente
  "status": "atrasado",
  "cliente_nome": "João Silva",
  ...
}
```

### 2. Resumo de Juros de Mora
```http
GET /api/parcelas/resumo-juros-mora
```

**Resposta:**
```json
{
  "total_multas": 150.50,
  "total_juros_mora": 25.30,
  "total_geral": 175.80
}
```

### 3. Registrar Pagamento
```http
POST /api/pagamentos
```

O sistema considera automaticamente:
- Valor original da parcela
- Multa acumulada
- Juros de mora acumulados

---

## 🤖 Job Automático (Scheduler)

**Frequência:** A cada 6 horas  
**Função:** Atualiza juros de mora de todas as parcelas atrasadas  
**Status:** ✅ Ativo (iniciado automaticamente com o backend)

Para verificar status do scheduler:
```bash
curl http://localhost:8001/api/scheduler/status
```

---

## 🔧 Configuração Personalizada

Ao criar um empréstimo, você pode personalizar as taxas:

```json
{
  "cliente_id": "uuid",
  "valor_principal": 10000,
  "taxa_juros_mensal": 5.0,
  "prazo_meses": 12,
  "metodo_calculo": "juros_simples",
  "taxa_multa_atraso": 3.0,        // Multa de 3% (personalizada)
  "taxa_juros_mora_diario": 0.05   // 0.05% ao dia (personalizada)
}
```

---

## 📊 Campos no Banco de Dados

### Modelo `Emprestimo`:
```python
taxa_multa_atraso: float = 2.0          # Multa % (padrão: 2%)
taxa_juros_mora_diario: float = 0.033   # Juros diário % (padrão: 0.033%)
```

### Modelo `Parcela`:
```python
valor_multa: float = 0.0          # Multa calculada
valor_juros_mora: float = 0.0     # Juros mora calculados
dias_atraso: int = 0              # Dias em atraso
status: str                        # pendente | atrasado | pago | parcial
```

---

## ✅ Validações e Regras

1. **Multa aplicada apenas uma vez** no primeiro dia de atraso
2. **Juros de mora acumulam diariamente** enquanto houver atraso
3. **Cálculo baseado no valor devido** (valor total - valor pago)
4. **Parcelas pagas não sofrem recálculo**
5. **Valores arredondados** para 2 casas decimais

---

## 🧪 Testes

Para testar o sistema:

```bash
cd /app/backend
python test_juros_mora.py
```

O script de teste:
- ✅ Cria empréstimo e parcela vencida
- ✅ Calcula juros de mora
- ✅ Atualiza valores no banco
- ✅ Verifica atualização em massa
- ✅ Gera resumo de juros

---

## 📈 Benefícios

1. **Automatização completa** - Sem necessidade de cálculos manuais
2. **Transparência** - Cliente vê exatamente quanto deve
3. **Flexibilidade** - Taxas configuráveis por empréstimo
4. **Conformidade** - Seguindo práticas do mercado financeiro
5. **Performance** - Cálculos otimizados com cache e jobs em background

---

## 🚨 Observações Importantes

- As taxas são definidas **por empréstimo**, não globalmente
- Valores padrão seguem práticas comuns do mercado brasileiro
- Sistema atualiza automaticamente, mas você pode forçar recálculo via API
- Juros de mora são calculados sobre o **valor devido** (não sobre o valor total original)

---

## 📞 Suporte

Para dúvidas ou customizações adicionais, consulte a documentação completa em `/docs` ou entre em contato com o suporte técnico.

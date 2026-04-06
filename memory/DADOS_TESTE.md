# 📊 Dados de Teste - GestorCred

## Resumo Executivo

Este documento descreve os dados de teste criados no sistema para facilitar o desenvolvimento e testes.

---

## 📈 Estatísticas Gerais

### Totais
- **Clientes**: 21 (incluindo 1 criado anteriormente)
- **Empréstimos**: 49 
- **Parcelas**: 578
- **Pagamentos Registrados**: 84

### Status das Parcelas
- ✅ **Pagas**: 84 parcelas (R$ 65.952,17)
- 📅 **Pendentes**: 468 parcelas (R$ 283.217,40)
- ⚠️ **Atrasadas**: 25 parcelas (R$ 16.954,94)
- ⏳ **Parciais**: 1 parcela (R$ 236,67 total, R$ 146,60 pago)

### Valores Financeiros
- **Valor Total Devido**: R$ 366.361,18
- **Valor Total Pago**: R$ 66.098,77
- **Valor Pendente**: R$ 300.262,41

---

## 👥 Clientes Criados (20 novos)

1. **João Silva** - 3 empréstimos
2. **Maria Santos** - 3 empréstimos
3. **Pedro Oliveira** - 2 empréstimos
4. **Ana Costa** - 3 empréstimos
5. **Carlos Souza** - 2 empréstimos
6. **Juliana Lima** - 3 empréstimos
7. **Roberto Alves** - 3 empréstimos
8. **Fernanda Rocha** - 3 empréstimos
9. **Paulo Mendes** - 2 empréstimos
10. **Camila Ferreira** - 1 empréstimo
11. **Lucas Barbosa** - 2 empréstimos
12. **Beatriz Martins** - 1 empréstimo
13. **Rafael Gomes** - 1 empréstimo
14. **Larissa Ribeiro** - 3 empréstimos
15. **Diego Cardoso** - 2 empréstimos
16. **Patrícia Araújo** - 2 empréstimos
17. **Felipe Nunes** - 3 empréstimos
18. **Mariana Dias** - 3 empréstimos
19. **Thiago Pereira** - 3 empréstimos
20. **Amanda Carvalho** - 3 empréstimos

---

## 💰 Características dos Empréstimos

### Valores Variados
- R$ 500,00
- R$ 1.000,00
- R$ 1.500,00
- R$ 2.000,00
- R$ 3.000,00
- R$ 5.000,00
- R$ 7.500,00
- R$ 10.000,00

### Taxas de Juros
- 3% a.m.
- 4% a.m.
- 5% a.m.
- 6% a.m.
- 7% a.m.
- 8% a.m.
- 10% a.m.

### Tipos de Juros
- Juros Simples
- Juros Compostos

### Número de Parcelas
- 3x
- 6x
- 10x
- 12x
- 18x
- 24x

---

## 📅 Distribuição Temporal

### Datas dos Empréstimos
- Criados entre 6 meses atrás e hoje
- Distribuição aleatória para simular cenário real

### Status das Parcelas
- **Parcelas Vencidas**: 70% pagas, 30% atrasadas
- **Parcelas Próximas**: Algumas com pagamento parcial
- **Parcelas Futuras**: Todas pendentes

---

## 🎯 Cenários de Teste Cobertos

### ✅ Cenários Implementados

1. **Clientes com múltiplos empréstimos**
   - Permite testar histórico e relacionamentos

2. **Empréstimos com diferentes valores**
   - Testa formatação e cálculos

3. **Diferentes taxas de juros**
   - Valida sistema de cálculo

4. **Juros simples e compostos**
   - Testa ambos os tipos de cálculo

5. **Parcelas em diferentes status**
   - Pagas, pendentes, atrasadas, parciais

6. **Pagamentos registrados**
   - Histórico de pagamentos disponível

7. **Parcelas atrasadas com multa e juros de mora**
   - Testa cálculo automático de penalidades

8. **Variação de número de parcelas**
   - De 3x até 24x

---

## 🔧 Como Usar os Dados

### Testar Funcionalidades

1. **Dashboard**: Visualize estatísticas gerais
2. **Clientes**: Browse pelos 20+ clientes
3. **Empréstimos**: Veja 48 empréstimos ativos
4. **Pagamentos**: 
   - Aba "Pendentes": 494 parcelas para pagamento
   - Aba "Histórico": 84 pagamentos já registrados
5. **Relatórios**: Gere relatórios com dados reais

### Testar Registro de Pagamentos

1. Acesse `/pagamentos`
2. Clique na aba "Parcelas Pendentes"
3. Use os filtros:
   - Status: Atrasadas (25 parcelas)
   - Status: Pendentes (468 parcelas)
4. Clique nos 3 pontinhos de qualquer parcela
5. Selecione "Registrar Pagamento"
6. Preencha o formulário e confirme

---

## 🗑️ Como Limpar os Dados de Teste

Se precisar limpar os dados de teste e recomeçar:

```bash
# CUIDADO: Isso apagará TODOS os dados exceto usuários
mongosh test_database --eval "
db.clientes.deleteMany({});
db.emprestimos.deleteMany({});
db.parcelas.deleteMany({});
db.pagamentos.deleteMany({});
"
```

Depois execute o seeder novamente:
```bash
cd /app/backend
python scripts/popular_dados_teste.py
```

---

## 📝 Notas Importantes

1. **Compatibilidade**: Todos os dados seguem o schema do MongoDB usado pelo sistema
2. **Integridade**: Relações entre clientes, empréstimos e parcelas estão corretas
3. **Realismo**: Dados simulam cenário real de uso
4. **Usuário**: Todos os dados pertencem ao usuário admin (admin@gestorcerd.com)
5. **Segurança**: CPFs são fictícios (gerados aleatoriamente)

---

## 🚀 Script de Geração

O script está localizado em:
```
/app/backend/scripts/popular_dados_teste.py
```

Para executar novamente:
```bash
cd /app/backend
python scripts/popular_dados_teste.py
```

---

**Última Atualização**: 06/04/2026  
**Versão**: 1.0

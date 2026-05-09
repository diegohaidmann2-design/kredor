# 🌱 Gerador de Clientes e Empréstimos

Script automático para gerar dados realistas de clientes, empréstimos e parcelas para testes.

## 📋 Características

### Clientes Gerados
- ✅ **Nomes realistas** - Lista de 50 nomes brasileiros
- ✅ **CPF válido** - Algoritmo de validação completo
- ✅ **Telefones** - Formato (DD) 9XXXX-XXXX
- ✅ **Endereços** - Cidades e estados reais do Brasil
- ✅ **CEPs** - Formato XXXXX-XXX
- ✅ **Emails** - Baseados no nome do cliente

### Empréstimos Gerados
- ✅ **Valores realistas** - De R$ 1.000 até R$ 100.000
  - 40% pequenos (R$ 1k - R$ 5k)
  - 35% médios (R$ 5k - R$ 15k)
  - 20% grandes (R$ 15k - R$ 50k)
  - 5% muito grandes (R$ 50k - R$ 100k)

- ✅ **Taxas de juros** - 0.5% a 8% ao mês
- ✅ **Prazos** - 6, 12, 18, 24, 36, 48 ou 60 meses
- ✅ **Métodos de cálculo**
  - 70% Tabela Price
  - 30% Juros Simples

- ✅ **Status com distribuição realista**
  - 70% Ativos
  - 20% Quitados
  - 10% Inadimplentes

- ✅ **Periodicidade**
  - 80% Mensal
  - 15% Quinzenal
  - 5% Semanal

- ✅ **Quantidade por cliente** - 1 a 3 empréstimos
  - 60% têm 1 empréstimo
  - 30% têm 2 empréstimos
  - 10% têm 3 empréstimos

### Parcelas Geradas
- ✅ **Status inteligente** - Baseado no status do empréstimo
  - Quitados: todas parcelas pagas
  - Inadimplentes: várias parcelas atrasadas
  - Ativos: mix de pagas e pendentes (80% pagamento em dia)

- ✅ **Multas e juros de mora**
  - 2% de multa sobre o valor
  - 0.1% ao dia de juros de mora

- ✅ **Datas realistas**
  - Quitados: 6 meses a 2 anos atrás
  - Inadimplentes: 3 meses a 1 ano atrás
  - Ativos: até 1 ano atrás

## 🚀 Como Usar

### Uso Básico (10 clientes)
```bash
cd /app/backend
python -m seeds.gerar_clientes_emprestimos
```

### Especificar Quantidade
```bash
# Gerar 5 clientes
python -m seeds.gerar_clientes_emprestimos 5

# Gerar 50 clientes
python -m seeds.gerar_clientes_emprestimos 50

# Gerar 100 clientes
python -m seeds.gerar_clientes_emprestimos 100
```

## 📊 Exemplo de Saída

```
╔══════════════════════════════════════════════════════════════════════════════╗
║              🌱 GERADOR DE CLIENTES E EMPRÉSTIMOS REALISTAS                  ║
╚══════════════════════════════════════════════════════════════════════════════╝

Quantidade a gerar: 5 clientes
Cada cliente terá de 1 a 3 empréstimos com parcelas completas

✅ Usando usuário: Diego Haidmann (diego.haidmann@gmail.com)

✅ Cliente 1/5: Fabio Miranda - Manaus/AM
   💰 Empréstimo 1: R$ 27,371.37 - 12x - Status: ativo

✅ Cliente 2/5: Leandro Cavalcanti - Brasília/DF
   💰 Empréstimo 1: R$ 3,971.74 - 6x - Status: ativo
   💰 Empréstimo 2: R$ 41,576.65 - 36x - Status: inadimplente

================================================================================
✅ Geração concluída com sucesso!
   📊 5 clientes criados
   💰 8 empréstimos criados
   📅 204 parcelas criadas
================================================================================
```

## 🔍 Verificar Dados Gerados

Você pode verificar o resumo dos dados criados:

```python
# Ver total de registros
db.clientes.count_documents({"deleted": {"$ne": True}})
db.emprestimos.count_documents({"deleted": {"$ne": True}})
db.parcelas.count_documents({})
```

## 💡 Casos de Uso

### 1. Testes de Performance
```bash
# Gerar 1000 clientes para testar paginação
python -m seeds.gerar_clientes_emprestimos 1000
```

### 2. Testes de Dashboard
```bash
# Gerar 50 clientes com dados variados
python -m seeds.gerar_clientes_emprestimos 50
```

### 3. Demonstração para Cliente
```bash
# Gerar 20 clientes com dados realistas
python -m seeds.gerar_clientes_emprestimos 20
```

### 4. Testes de Notificações
```bash
# Gerar 30 clientes (terá empréstimos com parcelas atrasadas)
python -m seeds.gerar_clientes_emprestimos 30
```

## 🎯 Benefícios

- ✅ **Dados Realistas** - CPFs válidos, endereços reais, valores coerentes
- ✅ **Variedade** - Mix de status, valores e prazos
- ✅ **Completo** - Gera clientes + empréstimos + parcelas de uma vez
- ✅ **Rápido** - Gera centenas de registros em segundos
- ✅ **Reutilizável** - Use sempre que precisar resetar ou adicionar dados
- ✅ **Inteligente** - Parcelas com status corretos baseados em datas

## ⚙️ Configuração

O script usa o primeiro usuário encontrado no banco de dados.
Certifique-se de ter executado o seeder de usuários antes:

```bash
python -m seeds.usuarios_seeder
```

## 📈 Estatísticas Típicas

Para **10 clientes** você terá aproximadamente:
- 👥 10 clientes
- 💰 15-20 empréstimos
- 📅 300-400 parcelas
- 💵 R$ 150.000 - R$ 500.000 em empréstimos

Para **50 clientes** você terá aproximadamente:
- 👥 50 clientes
- 💰 75-100 empréstimos
- 📅 1.500-2.000 parcelas
- 💵 R$ 750.000 - R$ 2.500.000 em empréstimos

Para **100 clientes** você terá aproximadamente:
- 👥 100 clientes
- 💰 150-200 empréstimos
- 📅 3.000-4.000 parcelas
- 💵 R$ 1.500.000 - R$ 5.000.000 em empréstimos

## 🛠️ Manutenção

### Adicionar Mais Nomes
Edite a lista `NOMES` no arquivo `gerar_clientes_emprestimos.py`

### Adicionar Mais Cidades
Edite a lista `CIDADES_ESTADOS` no arquivo

### Ajustar Faixas de Valores
Edite o array `faixas_valor` na função principal

### Ajustar Distribuição de Status
Edite os arrays `status_opcoes` e `status_pesos`

## 📝 Notas Importantes

1. O script NÃO limpa dados existentes, apenas adiciona novos
2. Cada execução gerará novos clientes independentes
3. CPFs são válidos mas aleatórios (não são de pessoas reais)
4. As datas são calculadas retroativamente para criar histórico
5. Parcelas atrasadas terão multas e juros de mora calculados

## 🤝 Integração com Sistema

Os dados gerados são 100% compatíveis com:
- ✅ Dashboard de estatísticas
- ✅ Relatórios financeiros
- ✅ Sistema de notificações
- ✅ Filtros e buscas
- ✅ Exportações
- ✅ Análises de inadimplência

---

**Desenvolvido para o Gestor de Crédito** 🚀

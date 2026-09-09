"""
Assistente Interno Inteligente - SEM LLM
Sistema baseado em regras e palavras-chave para responder perguntas sobre o Kredor
"""
import re
from typing import List, Dict, Tuple
from datetime import datetime


class AssistenteInterno:
    """Assistente baseado em regras para responder perguntas sobre o sistema"""
    
    def __init__(self):
        self.base_conhecimento = self._criar_base_conhecimento()
    
    def _criar_base_conhecimento(self) -> List[Dict]:
        """Cria base de conhecimento com perguntas e respostas"""
        return [
            # ==================== BOAS-VINDAS ====================
            {
                "keywords": ["oi", "olá", "ola", "hey", "bom dia", "boa tarde", "boa noite", "ola", "olar"],
                "categoria": "saudacao",
                "resposta": """👋 Olá! Bem-vindo ao Assistente do **Kredor**!

Posso ajudar com informações sobre:

📊 **Funcionalidades:**
• Como criar empréstimos
• Métodos de cálculo de juros
• Registro de pagamentos
• Prorrogação de empréstimos

💰 **Cálculos:**
• Diferença entre juros simples e compostos
• Como funciona Tabela Price
• Como funciona SAC
• Cálculo de multa e juros de mora

📋 **Gestão:**
• Cadastro de clientes
• Controle de parcelas
• Relatórios financeiros

❓ **Como posso ajudar você hoje?**"""
            },
            {
                "keywords": ["ajuda", "help", "comandos", "o que você faz", "o que voce faz"],
                "categoria": "ajuda",
                "resposta": """🤖 **Sou o Assistente do Kredor!**

Posso responder perguntas sobre:

1️⃣ **Empréstimos**
   - Como criar empréstimo
   - Métodos de cálculo
   - Prorrogação

2️⃣ **Cálculos de Juros**
   - Juros simples vs compostos
   - Tabela Price
   - SAC
   - Apenas juros

3️⃣ **Pagamentos**
   - Como registrar pagamento
   - Pagamento parcial
   - Quitação antecipada

4️⃣ **Clientes**
   - Cadastro
   - Gestão de carteira

5️⃣ **Relatórios**
   - Dashboard
   - Exportar dados

**Exemplos de perguntas:**
• "Como criar um empréstimo?"
• "O que é Tabela Price?"
• "Como prorrogar empréstimo?"
• "Como calcular juros de mora?"
"""
            },
            
            # ==================== EMPRÉSTIMOS ====================
            {
                "keywords": ["criar emprestimo", "novo emprestimo", "cadastrar emprestimo", "adicionar emprestimo"],
                "categoria": "emprestimos",
                "resposta": """📝 **Como Criar um Empréstimo:**

**Passo a passo:**

1️⃣ Vá em **"Empréstimos"** no menu
2️⃣ Clique em **"+ Novo Empréstimo"**
3️⃣ Preencha os dados:
   • **Cliente:** Selecione o cliente
   • **Valor:** Valor do empréstimo
   • **Taxa de Juros:** % mensal ou semanal
   • **Prazo:** Quantidade de meses/semanas
   • **Método de Cálculo:** Price, SAC, Juros Simples, etc.
   • **Dia de Vencimento:** Dia do mês para vencimento

4️⃣ Clique em **"Criar Empréstimo"**

✅ As parcelas são geradas automaticamente!

**Dica:** Use a **Simulação** antes de criar para ver como ficará."""
            },
            {
                "keywords": ["prorrogar", "prorrogacao", "prorrogação", "estender emprestimo", "prolongar"],
                "categoria": "prorrogacao",
                "resposta": """🕐 **Prorrogação de Empréstimos:**

**O que é:**
Permite estender o prazo do empréstimo, empurrando a data da última parcela para frente.

**Funciona apenas para:** Empréstimos **"Apenas Juros"**

**Como funciona:**
1. A última parcela (com capital) vira parcela de juros
2. Novas parcelas de juros são criadas
3. Nova última parcela com capital + juros é criada

**Como prorrogar:**

📋 **Da Listagem:**
1. Vá em "Empréstimos"
2. Clique no "⋮" do empréstimo
3. Clique em "🕐 Prorrogar Empréstimo"
4. Digite quantidade de períodos
5. Confirme

📄 **Dos Detalhes:**
1. Abra o empréstimo
2. Clique no "⋮" (menu ações)
3. Clique em "Prorrogar Empréstimo"

**Exemplo:**
Empréstimo de 3 meses prorrogado por 2 meses = Total de 6 parcelas"""
            },
            {
                "keywords": ["metodos de calculo", "métodos", "tabela price", "sac", "juros simples", "juros compostos", "apenas juros"],
                "categoria": "calculos",
                "resposta": """💰 **Métodos de Cálculo de Juros:**

**1. 📊 Juros Simples**
   • Juros sempre sobre o valor original
   • Parcelas iguais de principal + juros decrescentes
   • Mais simples de entender

**2. 📈 Juros Compostos**
   • Juros sobre juros (capitalização)
   • Crescimento exponencial
   • Mais usado em investimentos

**3. 📉 Tabela Price (SACFR)**
   • Parcelas **iguais** do início ao fim
   • Juros decrescem, amortização cresce
   • Mais popular no Brasil
   • Exemplo: R$ 334,38 todo mês

**4. 📊 SAC (Sistema de Amortização Constante)**
   • Parcelas **decrescentes**
   • Amortização constante
   • Juros sobre saldo devedor
   • Primeira parcela é a maior

**5. 💵 Apenas Juros**
   • Paga só juros durante o período
   • Capital todo na última parcela
   • Usado para prorrogações
   • Exemplo: R$ 1.000 juros + R$ 10.000 capital no final

**Qual escolher?**
• **Tabela Price:** Cliente prefere parcelas fixas
• **SAC:** Cliente quer pagar menos juros no total
• **Apenas Juros:** Flexibilidade de pagamento"""
            },
            
            # ==================== CÁLCULOS ESPECÍFICOS ====================
            {
                "keywords": ["tabela price", "price", "o que é price"],
                "categoria": "calculos",
                "resposta": """📉 **Tabela Price (SACFR):**

**Características:**
✅ Parcelas **iguais** do início ao fim
✅ Mais popular no Brasil
✅ Fácil para o cliente planejar
✅ Juros decrescem ao longo do tempo
✅ Amortização cresce ao longo do tempo

**Exemplo Prático:**
```
Empréstimo: R$ 10.000
Taxa: 10% a.m.
Prazo: 3 meses

Parcela 1: R$ 4.021,15
Parcela 2: R$ 4.021,15
Parcela 3: R$ 4.021,15

Total: R$ 12.063,45
Juros: R$ 2.063,45
```

**Composição das Parcelas:**
```
Mês 1: R$ 1.000 juros + R$ 3.021 principal
Mês 2: R$   698 juros + R$ 3.323 principal
Mês 3: R$   365 juros + R$ 3.656 principal
```

**Quando usar:**
• Cliente quer previsibilidade
• Parcelas fixas facilitam orçamento
• Empréstimos de médio/longo prazo"""
            },
            {
                "keywords": ["sac", "sistema de amortizacao constante", "amortização constante"],
                "categoria": "calculos",
                "resposta": """📊 **SAC - Sistema de Amortização Constante:**

**Características:**
✅ Parcelas **decrescentes**
✅ Amortização constante em todas as parcelas
✅ Juros calculados sobre saldo devedor
✅ Primeira parcela é a maior
✅ Última parcela é a menor
✅ Total de juros MENOR que Tabela Price

**Exemplo Prático:**
```
Empréstimo: R$ 10.000
Taxa: 10% a.m.
Prazo: 3 meses

Amortização: R$ 3.333,33 (todo mês)

Parcela 1: R$ 4.333,33 (R$ 3.333 + R$ 1.000 juros)
Parcela 2: R$ 4.000,00 (R$ 3.333 + R$   667 juros)
Parcela 3: R$ 3.666,67 (R$ 3.333 + R$   333 juros)

Total: R$ 12.000,00
Juros: R$ 2.000,00
```

**Vantagem sobre Price:**
📉 Total de juros: R$ 2.000 (SAC) vs R$ 2.063 (Price)

**Quando usar:**
• Cliente quer pagar menos juros no total
• Cliente consegue pagar parcela inicial maior
• Empréstimos de longo prazo"""
            },
            {
                "keywords": ["apenas juros", "bullet loan", "capital no final"],
                "categoria": "calculos",
                "resposta": """💵 **Apenas Juros (Capital no Final):**

**Características:**
✅ Paga **apenas juros** durante o período
✅ Capital todo na **última parcela**
✅ Ideal para **prorrogações**
✅ Flexibilidade para o cliente
✅ Usado em empréstimos de curto prazo

**Exemplo Prático:**
```
Empréstimo: R$ 10.000
Taxa: 10% a.m.
Prazo: 3 meses

Parcela 1: R$ 1.000 (só juros)
Parcela 2: R$ 1.000 (só juros)
Parcela 3: R$ 11.000 (R$ 10.000 capital + R$ 1.000 juros)

Total: R$ 13.000
Juros: R$ 3.000
```

**Vantagens:**
• Parcelas menores durante o período
• Cliente tem tempo para organizar o capital
• Pode ser prorrogado várias vezes

**Prorrogação:**
Quando chega a última parcela, pode estender:
```
Original (3 meses):
Mês 1-2: R$ 1.000 (juros)
Mês 3: R$ 11.000 (capital)

Prorrogado +2 meses:
Mês 1-4: R$ 1.000 (juros)
Mês 5: R$ 11.000 (capital)
```

**Quando usar:**
• Empréstimos de curto prazo
• Cliente precisa de flexibilidade
• Situações temporárias de fluxo de caixa"""
            },
            {
                "keywords": ["juros de mora", "multa", "atraso", "inadimplencia", "inadimplência"],
                "categoria": "calculos",
                "resposta": """⚠️ **Juros de Mora e Multa por Atraso:**

**Valores Padrão do Sistema:**
• **Multa:** 2% sobre o valor da parcela
• **Juros de Mora:** 0,033% ao dia (1% ao mês)

**Como é Calculado:**

**Exemplo de Parcela Atrasada:**
```
Valor da Parcela: R$ 1.000,00
Dias de Atraso: 30 dias

Multa (2%): R$ 20,00
Juros de Mora (30 dias x 0,033%): R$ 10,00

Total a Pagar: R$ 1.030,00
```

**Cálculo Detalhado:**
```
Multa = Valor × 2%
     = 1.000 × 0,02
     = R$ 20,00

Juros = Valor × 0,033% × Dias
      = 1.000 × 0,00033 × 30
      = R$ 10,00 (aproximadamente 1%)
```

**Sistema Automático:**
✅ O sistema calcula **automaticamente** quando a parcela está atrasada
✅ Aparece no detalhes da parcela
✅ É somado ao valor total a pagar

**Configuração:**
Você pode alterar esses valores em:
**Configurações → Sistema → Juros e Multas**"""
            },
            
            # ==================== PAGAMENTOS ====================
            {
                "keywords": ["registrar pagamento", "pagar", "pagamento", "como pagar", "lançar pagamento"],
                "categoria": "pagamentos",
                "resposta": """💰 **Como Registrar Pagamento:**

**3 Formas de Registrar:**

**1️⃣ Da Listagem de Empréstimos (MAIS RÁPIDO!):**
   • Vá em "Empréstimos"
   • Clique no botão verde **"💰 Pagar"**
   • Preencha os dados do pagamento
   • Confirme

**2️⃣ Dos Detalhes do Empréstimo:**
   • Abra o empréstimo
   • Clique em uma parcela pendente
   • Modal de pagamento abre
   • Preencha e confirme

**3️⃣ Do Menu de Ações:**
   • Clique no "⋮" do empréstimo
   • "Registrar Pagamento"
   • Escolha a parcela
   • Preencha e confirme

**Dados do Pagamento:**
• **Valor Pago:** Quanto o cliente pagou
• **Data do Pagamento:** Quando pagou
• **Forma de Pagamento:** Dinheiro, PIX, etc.
• **Observações:** (opcional)

**Pagamento Parcial:**
✅ Pode pagar menos que o valor total
✅ Sistema marca como "Parcialmente Pago"
✅ Saldo restante fica registrado

**Quitação Antecipada:**
✅ Pode quitar todas as parcelas de uma vez
✅ Use a opção "Quitar Empréstimo" no menu"""
            },
            {
                "keywords": ["pagamento parcial", "pagar menos", "valor menor"],
                "categoria": "pagamentos",
                "resposta": """📊 **Pagamento Parcial:**

**O que é:**
Quando o cliente paga **menos** que o valor total da parcela.

**Como funciona:**
✅ Sistema aceita qualquer valor
✅ Parcela fica como **"Parcialmente Pago"**
✅ Saldo restante é calculado automaticamente
✅ Cliente pode completar depois

**Exemplo:**
```
Valor da Parcela: R$ 1.000,00
Pagamento 1: R$ 600,00
Status: Parcialmente Pago
Saldo Restante: R$ 400,00

Pagamento 2: R$ 400,00
Status: Pago
Saldo: R$ 0,00
```

**No Sistema:**
1. Registre o pagamento normalmente
2. Digite o valor que o cliente pagou
3. Sistema calcula o restante
4. Parcela mostra saldo pendente

**Dica:**
💡 Use "Observações" para anotar acordos de pagamento parcial"""
            },
            
            # ==================== CLIENTES ====================
            {
                "keywords": ["cadastrar cliente", "novo cliente", "adicionar cliente", "criar cliente"],
                "categoria": "clientes",
                "resposta": """👥 **Como Cadastrar Cliente:**

**Passo a passo:**

1️⃣ Vá em **"Clientes"** no menu
2️⃣ Clique em **"+ Novo Cliente"**
3️⃣ Preencha os dados:

**Dados Obrigatórios:**
• **Nome Completo**
• **CPF ou CNPJ** (validado automaticamente)
• **Telefone** (com DDD)

**Dados Opcionais:**
• Email
• Endereço completo
• Data de nascimento
• Observações

4️⃣ Clique em **"Salvar"**

✅ Cliente criado e pronto para receber empréstimos!

**Validações Automáticas:**
• ✅ CPF/CNPJ válido
• ✅ Telefone no formato correto
• ✅ Email válido (se informado)

**Dicas:**
💡 Preencha o máximo de informações para facilitar contato
💡 Use "Observações" para anotações importantes
💡 Pode editar depois se precisar"""
            },
            
            # ==================== RELATÓRIOS ====================
            {
                "keywords": ["relatorio", "relatório", "dashboard", "exportar", "pdf", "excel"],
                "categoria": "relatorios",
                "resposta": """📊 **Relatórios e Exportações:**

**Dashboard:**
📍 Menu → Dashboard

Mostra:
• Total emprestado
• Total a receber
• Total recebido
• Taxa de inadimplência
• Gráficos de evolução
• Distribuição por status

**Exportar Empréstimos:**

**PDF:**
1. Abra o empréstimo
2. Clique no "⋮" (menu)
3. "Compartilhar PDF"
4. PDF é baixado automaticamente

**Conteúdo do PDF:**
✅ Dados do cliente
✅ Informações do empréstimo
✅ Resumo financeiro (com juros!)
✅ Tabela de parcelas
✅ Status de pagamento

**Excel:**
1. Abra o empréstimo
2. Menu → "Exportar Excel"
3. Planilha completa é baixada

**Relatório de Parcelas:**
📍 Empréstimo → Parcelas
• Lista completa de parcelas
• Status de cada uma
• Valores e datas
• Histórico de pagamentos"""
            },
            
            # ==================== DÚVIDAS COMUNS ====================
            {
                "keywords": ["diferenca", "diferença", "price vs sac", "qual melhor"],
                "categoria": "comparacao",
                "resposta": """⚖️ **Price vs SAC - Qual é Melhor?**

**Comparação Direta:**

| Aspecto | Tabela Price | SAC |
|---------|--------------|-----|
| **Parcelas** | Iguais | Decrescentes |
| **Primeira Parcela** | Menor | Maior |
| **Última Parcela** | Igual primeira | Menor |
| **Total de Juros** | Maior | Menor |
| **Previsibilidade** | Alta | Média |
| **Popular em** | Geral | Imóveis |

**Exemplo R$ 10.000 - 10% a.m. - 3 meses:**

**Tabela Price:**
```
Parcela 1: R$ 4.021
Parcela 2: R$ 4.021
Parcela 3: R$ 4.021
Total Juros: R$ 2.063
```

**SAC:**
```
Parcela 1: R$ 4.333
Parcela 2: R$ 4.000
Parcela 3: R$ 3.667
Total Juros: R$ 2.000
```

**Quando Usar Price:**
✅ Cliente quer parcelas fixas
✅ Orçamento previsível
✅ Empréstimos curto/médio prazo

**Quando Usar SAC:**
✅ Cliente pode pagar mais no início
✅ Quer economia de juros
✅ Empréstimos de longo prazo

**Recomendação:**
💡 **Price** é mais comum e fácil de entender
💡 **SAC** economiza juros mas exige parcela inicial maior"""
            },
            {
                "keywords": ["simular", "simulacao", "simulação", "calcular antes"],
                "categoria": "simulacao",
                "resposta": """🧮 **Simulação de Empréstimos:**

**Como Simular:**

1️⃣ Vá em **"Empréstimos"**
2️⃣ Clique em **"+ Novo Empréstimo"**
3️⃣ Preencha os dados básicos
4️⃣ Clique em **"Simular"** (antes de criar)

**O que a Simulação Mostra:**
✅ Valor de cada parcela
✅ Total a pagar
✅ Total de juros
✅ Tabela completa de parcelas
✅ Datas de vencimento
✅ Composição (principal + juros)

**Vantagens:**
• Ver como fica antes de criar
• Comparar métodos diferentes
• Mostrar para o cliente
• Tomar decisão informada

**Pode Simular:**
✅ Tabela Price
✅ SAC
✅ Juros Simples
✅ Juros Compostos
✅ Apenas Juros

**Dica:**
💡 Simule com diferentes métodos e compare!
💡 Mostre a simulação para o cliente antes de fechar o acordo"""
            },
            {
                "keywords": ["como funciona o sistema", "funcionalidades", "o que o sistema faz"],
                "categoria": "sistema",
                "resposta": """🎯 **Kredor - Visão Geral:**

**O que é:**
Sistema completo de gestão de empréstimos com cálculo automático de juros, controle de parcelas e cobranças.

**Principais Funcionalidades:**

📋 **Gestão de Clientes**
• Cadastro completo
• Validação de CPF/CNPJ
• Histórico de empréstimos

💰 **Empréstimos**
• 5 métodos de cálculo
• Geração automática de parcelas
• Simulação antes de criar
• Prorrogação (apenas juros)

💵 **Pagamentos**
• Registro rápido
• Pagamento parcial
• Múltiplas formas de pagamento
• Histórico completo

📊 **Relatórios**
• Dashboard com métricas
• Exportação PDF/Excel
• Controle de inadimplência
• Gráficos evolutivos

🔔 **Automações**
• Cálculo automático de multa/juros
• Atualização de status
• Jobs periódicos
• Notificações

**Diferenciais:**
✅ Sem necessidade de cálculos manuais
✅ Múltiplos métodos de juros
✅ Prorrogação de empréstimos
✅ Interface intuitiva
✅ Relatórios profissionais"""
            },
            
            # ==================== FALLBACK ====================
            {
                "keywords": [""],  # Sempre vai dar match (fallback)
                "categoria": "fallback",
                "resposta": """❓ **Não entendi sua pergunta, mas posso ajudar com:**

**💰 Empréstimos:**
• "Como criar um empréstimo?"
• "Como prorrogar empréstimo?"
• "O que é Tabela Price?"

**📊 Cálculos:**
• "Diferença entre Price e SAC"
• "Como calcular juros de mora?"
• "O que é apenas juros?"

**💵 Pagamentos:**
• "Como registrar pagamento?"
• "Como fazer pagamento parcial?"

**👥 Clientes:**
• "Como cadastrar cliente?"

**📈 Relatórios:**
• "Como exportar para PDF?"
• "Como ver dashboard?"

**Tente perguntar de outra forma ou escolha um tópico acima!**"""
            }
        ]
    
    def _normalizar_texto(self, texto: str) -> str:
        """Normaliza texto removendo acentos e convertendo para minúsculas"""
        texto = texto.lower().strip()
        # Remover pontuação
        texto = re.sub(r'[^\w\s]', ' ', texto)
        # Remover espaços extras
        texto = re.sub(r'\s+', ' ', texto)
        return texto
    
    def _calcular_score(self, pergunta: str, keywords: List[str]) -> float:
        """Calcula score de relevância baseado em palavras-chave"""
        pergunta_norm = self._normalizar_texto(pergunta)
        palavras_pergunta = set(pergunta_norm.split())
        
        if not keywords or keywords == [""]:
            return 0.0
        
        # Contar quantas keywords estão presentes
        matches = 0
        for keyword in keywords:
            keyword_norm = self._normalizar_texto(keyword)
            keyword_palavras = set(keyword_norm.split())
            
            # Se todas as palavras da keyword estão na pergunta
            palavras_em_comum = palavras_pergunta.intersection(keyword_palavras)
            if palavras_em_comum:
                # Match parcial: dar pontos proporcionais
                proporcao = len(palavras_em_comum) / len(keyword_palavras)
                matches += proporcao * len(keyword_palavras)
                
                # Bonus se tiver frase completa
                if keyword_norm in pergunta_norm:
                    matches += len(keyword_palavras)
        
        # Score normalizado
        total_palavras_keywords = sum(len(self._normalizar_texto(k).split()) for k in keywords if k)
        if total_palavras_keywords == 0:
            return 0.0
        
        score = matches / total_palavras_keywords
        return min(score, 1.5)  # Permitir score > 1 para matches muito bons
    
    def processar_mensagem(self, mensagem: str, contexto_usuario: Dict = None) -> str:
        """Processa mensagem e retorna resposta mais relevante"""
        
        # Calcular scores para todas as respostas
        scores = []
        for item in self.base_conhecimento:
            score = self._calcular_score(mensagem, item["keywords"])
            scores.append((score, item))
        
        # Ordenar por score (maior primeiro)
        scores.sort(key=lambda x: x[0], reverse=True)
        
        # Pegar a melhor resposta
        melhor_score, melhor_item = scores[0]
        
        # Se o score for muito baixo, usar fallback
        if melhor_score < 0.1 and melhor_item["categoria"] != "fallback":
            # Buscar fallback
            for item in self.base_conhecimento:
                if item["categoria"] == "fallback":
                    return item["resposta"]
        
        resposta = melhor_item["resposta"]
        
        # Adicionar contexto do usuário se disponível
        if contexto_usuario and melhor_item["categoria"] not in ["saudacao", "ajuda", "fallback"]:
            contexto_texto = self._formatar_contexto_usuario(contexto_usuario)
            resposta = f"{resposta}\n\n{contexto_texto}"
        
        return resposta
    
    def _formatar_contexto_usuario(self, contexto: Dict) -> str:
        """Formata contexto do usuário para incluir na resposta"""
        if not contexto:
            return ""
        
        texto = "---\n📊 **Seu Resumo:**\n"
        
        if "total_clientes" in contexto:
            texto += f"• Clientes cadastrados: {contexto['total_clientes']}\n"
        
        if "total_emprestimos" in contexto:
            texto += f"• Total de empréstimos: {contexto['total_emprestimos']}\n"
        
        if "emprestimos_ativos" in contexto:
            texto += f"• Empréstimos ativos: {contexto['emprestimos_ativos']}\n"
        
        return texto


# Instância global do assistente
assistente = AssistenteInterno()

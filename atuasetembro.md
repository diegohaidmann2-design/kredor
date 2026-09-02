# Atualizações — Setembro (GestorCred)

Documento de planejamento das próximas atualizações do **GestorCred**, com base em (1) análise competitiva do **CobraFácil** (inspeção das funções via bundle do app) e (2) **diagnóstico dos dados reais** do nosso próprio sistema.

---

## 1. Diagnóstico do negócio (dados reais do app)
Análise da base `gestorcred`:
- **Negócio = empréstimo pessoal / microcrédito** (SaaS multi-tenant por assinatura: planos trial/profissional/enterprise).
- 81 empréstimos, R$ 196 mil de principal, **ticket médio ~R$ 2,4 mil** (R$100 a R$14 mil).
- Modalidade dominante: **"apenas juros" (74%)**; depois juros simples e poucos na Price.
- Periodicidade **mensal** (74) e semanal (4).
- Cobrança **via WhatsApp** intensa (12 templates, conexões, fila).
- Situação: 54 ativos, 25 quitados, 2 inadimplentes; parcelas: 193 pagas, 87 pendentes, **27 atrasadas**.
- **Vendas: ZERO** — não há produtos/mercadoria.

### Veredito sobre "Vendas / Crediário"
❌ **Não vale a pena implementar Vendas agora.** O público **empresta dinheiro, não vende produtos**. Um módulo de crediário só faria sentido num **pivô estratégico** para atender lojistas — não é ganho rápido e ficaria ocioso para 100% dos usuários atuais.

---

## 2. Roadmap revisado (priorizado para o negócio de empréstimo)

### 🥇 P0 — Consultas de crédito (CPF/CNPJ)  ⭐⭐
Maior valor: já temos 27 parcelas atrasadas + 2 inadimplentes. Consultar o cliente **antes** de liberar reduz calote.
- Realizar consulta, **Carteira**, **Histórico** e detalhe da consulta.
- **PDF** da consulta anexável ao cliente.
- **Monetizável** (cobrança por consulta / limites por plano).
- Provedor a definir (ex.: Datrin/Serasa/SPC/Boa Vista).

### 🥈 P1 — Agenda / Calendário de cobrança
Uso diário: com 87 pendentes + 27 atrasadas, ver "quem vence hoje / quem está atrasado" com atalho pro WhatsApp que já temos.

### 🥉 P1 — Cadastro público do cliente + Aprovação
- **Link público** onde o próprio cliente preenche a ficha (dados + documentos).
- **Fluxo de aprovação** antes de liberar crédito.

### P2 — CCB (Cédula de Crédito Bancário) com assinatura
- Geração da CCB do empréstimo + **assinatura digital do mutuário**.

### P2 — Links de pagamento / Checkout de cobrança
- Gerar **link de pagamento** de uma parcela para enviar ao cliente.

### P2 — PWA + Push notifications (cobrador em campo)
- App **instalável** no celular, **push** de vencimentos/recebimentos, "receber em 2 toques".

### P3 — Extras
- Veículos (garantia), afiliados + métricas de atribuição, inbox de Conversas, relatórios automáticos por e-mail.

---

## 3. Melhorias de experiência (transversais)
- **Modo claro (light theme)** com toggle (hoje só tema escuro).
- **Login com Google** (opcional, além do JWT atual).

---

## 4. Fora de escopo (por ora)
- **Vendas a Prazo / Crediário** — reavaliar só se houver decisão de atender lojistas.

---

## 5. Ordem sugerida de execução
1. Consultas de crédito (P0)
2. Agenda de cobrança (P1)
3. Cadastro público + Aprovação (P1)
4. CCB + Links de pagamento (P2)
5. PWA + Push (P2)

> Cada item será implementado e validado (testing agent) antes de seguir para o próximo.

---

## Changelog
- **set/2026** — Correção do **Score de Clientes**: o score não era recalculado automaticamente (nenhum cliente tinha `score_atual`, todos apareciam como 60 em `/analise/clientes`). Adicionado recálculo automático ao **registrar** e **estornar** pagamento e no **job de inadimplência**; feito **backfill** dos clientes existentes.

_Documento criado/atualizado em setembro/2026 — base para as próximas sprints do GestorCred._

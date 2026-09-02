# Atualizações — Setembro (GestorCred)

Documento de planejamento das próximas atualizações do **GestorCred**, com base na análise competitiva do **CobraFácil** (inspeção das funções via bundle do app: rotas, páginas e permissões).

---

## 1. Contexto
O CobraFácil é um SPA (React/Vite + Supabase) focado em cobradores e microempresas de crédito/vendas. A análise revelou funções que ainda **não existem** no GestorCred e que fazem sentido para o nosso produto ("Gestão Completa de Cobranças, Empréstimos e **Vendas**").

### O que já somos mais fortes (manter)
Portal do cliente, contratos, auditoria completa, multi-gateway de assinatura (Stripe/Asaas/SyncPay), WhatsApp com anti-spam, 2FA, assistente IA, cupons, lixeira/soft-delete, relatórios PDF + Excel.

---

## 2. Roadmap de atualizações (priorizado)

### 🥇 P0 — Módulo de Vendas a Prazo / Crediário  ⭐⭐ (maior ganho)
Completa o nome do produto e reaproveita clientes/parcelas/pagamentos/WhatsApp já existentes.
- Cadastro de **produtos/itens** (nome, preço, estoque opcional).
- **Venda parcelada** por cliente (crediário): entrada, nº de parcelas, juros opcional.
- **Adicionais na venda** (frete, taxas, acréscimos) — inspirado no "SaleAddonsEditor".
- Saldo devedor de crediário integrado ao mesmo fluxo de cobrança/WhatsApp/relatórios.
- **Relatórios de vendas** (por período, por cliente, por produto).
- Permissão de acesso: `gerenciar_vendas` / `gerenciar_produtos`.

### 🥈 P1 — Consultas de crédito integradas  ⭐⭐ (alto valor, monetizável)
- Realizar consulta de **CPF/CNPJ** (provedor tipo Datrin/Serasa/SPC/Boa Vista — a definir).
- **Carteira** de consultas, **histórico** e **detalhe** da consulta.
- **PDF** da consulta para anexar ao processo do cliente.
- Possibilidade de **monetização** (cobrança por consulta / limites por plano).

### 🥉 P1 — Agenda / Calendário de cobrança
- Visão de **vencimentos do dia/semana** (parcelas a receber).
- Rota de cobrança / lembretes; integração com WhatsApp já existente.

### P1 — Cadastro público do cliente + Aprovação
- **Link público** onde o próprio cliente preenche a ficha (dados + documentos).
- **Fluxo de aprovação** do cliente antes de liberar crédito/venda.

### P2 — CCB (Cédula de Crédito Bancário) com assinatura
- Geração da **CCB** do empréstimo.
- **Assinatura do mutuário** (link de assinatura para o cliente).

### P2 — Links de pagamento / Checkout de cobrança
- Gerar **link de pagamento** de uma parcela/venda para enviar ao cliente.

### P2 — PWA + Push notifications (cobrador em campo)
- App **instalável** no celular (PWA).
- **Push** de vencimentos/recebimentos.
- Ação rápida: marcar parcela como paga em poucos toques.

### P3 — Veículos (garantia/financiamento)
- Cadastro de veículo como **garantia** do empréstimo.

### P3 — Extras de crescimento
- Programa de **afiliados** + métricas de atribuição (UTM).
- Inbox de **Conversas** unificado.
- **Relatórios automáticos** agendados por e-mail.

---

## 3. Melhorias de experiência (transversais)
- **Modo claro (light theme)** com toggle (hoje só temos tema escuro).
- **Login com Google** (opcional, além do JWT atual).

---

## 4. Ordem sugerida de execução
1. Vendas a Prazo / Crediário (P0)
2. Consultas de crédito (P1)
3. Agenda de cobrança + Cadastro público/Aprovação (P1)
4. PWA + Push (P2)
5. CCB + Links de pagamento (P2)
6. Veículos + extras (P3)

> Observação: cada item será implementado e validado (testing agent) antes de seguir para o próximo.

---

_Documento criado em setembro/2026 — base para as próximas sprints do GestorCred._

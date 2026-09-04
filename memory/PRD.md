# GestorCred — PRD

## Contexto
Sistema de Gestão de Empréstimos importado (backup MongoDB `backup-20260902-182538`) rodando com backend FastAPI + frontend React + MongoDB via supervisor. URL pública: https://dcc8680e-8d69-4773-ab59-78dfb7dfe969.preview.emergentagent.com

## Personas
- **Dono/Agiotagem**: gerencia carteira própria, clientes, empréstimos e consultas.
- **Funcionário**: opera para o dono (herda plano e carteira via `owner_id`).
- **Admin/SuperAdmin**: gerencia usuários, assinaturas, preços de consulta e carteiras.

## Módulos Existentes
Dashboard, Clientes, Empréstimos (Ativos/Abertos/Quitados), Simulação, Pagamentos, Agenda, Consultas (CPF/CNPJ/Telefone/Nome/Dívidas/Facial via LosDados), Análise/Score, Relatórios, Contratos, WhatsApp, Assinatura, Suporte, Portal do Cliente, Admin (Usuários, Assinaturas, Transações, Cupons, Scheduler, Backup, Suporte).

## Implementações desta sessão (2026-09-04)

### 1) Import do projeto + banco (2026-09-04)
- Extraído `backup-20260902-182538.tar.gz`, restaurado via `mongorestore` (58 coleções, 8459 docs).
- Criados `/app/backend/.env` e `/app/frontend/.env` conforme fornecido.
- `iniciar.sh` valida deps e services; supervisor mantém backend+frontend+mongo up.

### 2) Carteira de Consultas Premium (2026-09-04)
**Objetivo:** transformar Consultas em recurso PRO com carteira paga por consulta.

**Backend**
- Nova coleção `carteiras` (uma por `owner_id`, funcionários compartilham).
- Nova coleção `carteira_movimentos` (tipos: recarga/consumo/bonus/estorno/ajuste).
- Nova coleção `consultas_precos` (7 tipos com preços editáveis pelo admin).
- Nova coleção `carteira_recargas` (checkout PIX Asaas/SyncPay + polling).
- `services/carteira_service.py`: obter/criar carteira, aplicar movimento atômico, débito por consulta, estorno, crédito por webhook, ajuste admin, dashboard.
- `routes/carteira.py`: `/api/carteira/{,precos,movimentos,gateways,recarga/asaas,recarga/syncpay,recarga/{id}/status}`.
- `routes/admin_carteiras.py`: `/api/admin/carteiras/{dashboard,,precos,precos/{tipo},{owner_id},{owner_id}/movimentos,{owner_id}/ajuste}`.
- `routes/consultas.py`: integrado `_cobrar_ou_bloquear` (retorna 402 SALDO_INSUFICIENTE) + `_debitar_seguro` em todos os 7 endpoints.
- Webhooks Asaas + SyncPay agora identificam `carteira_recarga_*` no `externalReference` e creditam a carteira idempotentemente.
- Bônus inicial de R$ 5,00 na criação da carteira. Preços padrão: CPF/CNPJ 0.90 · Telefone/Nome 0.50 · Dívidas 2.50 · Facial 5.00.

**Frontend**
- `Sidebar.js`: badge "PRO" no item Consultas + novo item "Carteira" + item admin "Carteiras & Preços".
- `pages/Carteira.js`: página completa com saldo, cards resumo, tabela de preços, movimentações filtráveis, modal de recarga PIX (Asaas/SyncPay) com QR code + polling automático de status.
- `pages/AdminCarteiras.js`: dashboard admin (saldo total, receita 30d, consumo, recargas), listagem de carteiras com busca, edição inline de preços, modal de ajuste manual e modal de detalhes.
- `pages/Consultas.js`: barra de saldo + preço no header, banner de saldo insuficiente com CTA "Recarregar carteira", tratamento de HTTP 402.
- `api/api.js`: novos clients `carteiraAPI` e `adminCarteirasAPI`.
- `App.js`: rotas `/carteira` (ProtectedRoute) e `/admin/carteiras` (AdminRoute).

**Testado via curl (100% verde)**
- Novo usuário → carteira criada com R$ 5,00 bônus ✅
- Consulta CPF débito R$ 0,90, saldo 5,00 → 4,10 ✅
- Facial (R$ 5) com saldo 4,10 → HTTP 402 SALDO_INSUFICIENTE ✅
- Admin: dashboard, listagem, ajuste manual +R$50, edição preço CPF 0,90→1,20 ✅
- Frontend visualizado: Carteira (saldo, preços, movimentações), Consultas (barra saldo), Admin (dashboard, carteiras, preços) ✅

## Backlog / Próximos Passos
- **P1**: Testes automáticos com `testing_agent` cobrindo o fluxo end-to-end de recarga real (requer credenciais Asaas/SyncPay reais no admin).
- **P1**: Notificação in-app quando saldo cai abaixo de threshold configurável (ex.: menor que 5x o custo médio).
- **P2**: Auto-recharge configurável (recarga automática ao atingir saldo mínimo, via cartão salvo).
- **P2**: Relatório contábil da receita da carteira (mensal, exportável) na área admin.
- **P2**: Cupons de recarga (dar R$ X extra ao recarregar R$ Y).

## Arquivos-chave
- Backend: `services/carteira_service.py`, `routes/carteira.py`, `routes/admin_carteiras.py`, `routes/consultas.py`, `routes/assinaturas.py` (webhooks).
- Frontend: `pages/Carteira.js`, `pages/AdminCarteiras.js`, `pages/Consultas.js`, `components/Sidebar.js`, `api/api.js`, `App.js`.

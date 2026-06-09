# Gestor Cred - Sistema de Gestão de Empréstimos a Juros

## Problema Original
"importei meu projeto, coloque para rodar" — Usuário importou um projeto existente (Gestor Cred v2.1.0) e solicitou que fosse colocado em execução.

## Arquitetura
- **Backend**: FastAPI 0.110.1 (Python) — `/app/backend`
- **Frontend**: React 19 + CRA/Craco + TailwindCSS + Radix UI — `/app/frontend`
- **Banco**: MongoDB (Motor async)
- **Serviços via Supervisor**: backend (porta 8001), frontend (porta 3000), mongodb

## Tarefas Realizadas (09/06/2026)
- Criado `/app/backend/.env` com `MONGO_URL`, `DB_NAME=gestorcred_dev`, `JWT_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `CORS_ORIGINS=*`, `APP_URL` apontando para preview.
- Criado `/app/frontend/.env` com `REACT_APP_BACKEND_URL` (preview emergent).
- Instaladas dependências Python (`pip install -r requirements.txt`) e Node (`yarn install`).
- Reiniciado supervisor — backend e frontend rodando, landing page carregando OK.

## Status
- Backend: ✅ rodando em http://0.0.0.0:8001 (`{"status":"online","version":"2.1.0"}`)
- Frontend: ✅ rodando, landing page "GestorCred" renderizando corretamente
- MongoDB: ✅ rodando localmente

## Features do App (já implementadas no código)
- Gestão de clientes, empréstimos, parcelas, pagamentos
- Score de crédito, auditoria, notificações
- Portal do cliente, contratos
- Integrações: Stripe, MercadoPago, SyncPay PIX, Asaas, SMTP, WhatsApp, LLM (Emergent)
- Scheduler de jobs automáticos (vencimentos, juros de mora)

## Backlog / Próximos Passos
- **P0**: Configurar credenciais reais (Stripe, SMTP, EMERGENT_LLM_KEY) se necessário
- **P1**: Testar fluxos de autenticação e CRUD principais
- **P2**: Configurar webhooks de gateways de pagamento

## Credenciais
- Nenhuma credencial seed criada. Para usar, crie um usuário via `/api/auth/registro` ou execute scripts em `/app/backend/seeds/`.

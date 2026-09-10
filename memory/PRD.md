# GestorCred / Kredor — PRD

## Problema / Objetivo
Projeto importado (SaaS de gestão de empréstimos e cobrança automática via PIX/WhatsApp).
Pedido do usuário: rodar `iniciar.sh`, colocar tudo no ar e importar o banco anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`, entrada `server.py` -> `main.py`), scheduler APScheduler (RUN_SCHEDULER=true).
- Frontend: React (`/app/frontend`).
- DB: MongoDB local (`gestorcred`).
- Integrações no código: Stripe, MercadoPago, SyncPay (PIX), LosDados, SMTP, Turnstile, Evolution API (WhatsApp), Emergent LLM.

## O que foi feito (2026-09-10)
- Criados `backend/.env` e `frontend/.env` com as variáveis fornecidas pelo usuário.
  - `REACT_APP_BACKEND_URL` e `APP_URL` preenchidos com a URL pública do preview (não podem ficar vazios neste ambiente).
- Instaladas dependências do backend (requirements.txt); node_modules já presente.
- Serviços no ar via supervisor: backend (200), frontend (200), mongodb, scheduler (16 jobs).
- Corrigidos 14 erros de lint (imports duplicados F811) em auth.py, emprestimos.py, parcelas.py, whatsapp.py, superadmin.py.
- Banco importado de `backup-20260910-121145.tar.gz` (mongodump) via `mongorestore --drop`:
  8862 documentos. Coleções principais: usuarios(8), clientes(47), emprestimos(91),
  parcelas(346), pagamentos(211), carteiras(3).

## Observações
- Senhas dos usuários vêm do dump (bcrypt) — não conhecidas. Ver `memory/test_credentials.md`.
- `FIELD_ENCRYPTION_KEY` fornecida pelo usuário deve corresponder à do dump para decriptar campos sensíveis (ex.: CPF).

## Backlog / Próximos passos
- Validar login com uma conta real (senha do usuário) e navegar pelo dashboard.
- Configurar SMTP e webhooks de pagamento (Stripe/MercadoPago/SyncPay) se for para produção.

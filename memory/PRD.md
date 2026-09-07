# GestorCred — PRD / Handoff

## Problem statement original
Importar projeto existente, rodar `iniciar.sh`, colocar tudo no ar, importar o banco anexado e usar a `.env` fornecida.

## Stack
- Backend: FastAPI (entry `server.py` → `main.py`), MongoDB (motor), APScheduler, emergentintegrations/litellm.
- Frontend: React (CRA), TailwindCSS, framer-motion, axios. Contextos: Auth, Portal, Theme.
- DB: MongoDB local, database `gestorcred`.

## Setup realizado (07/09/2026 — sessão atual, novo ambiente)
- `.env` do backend recriado com a env fornecida (APP_URL preenchido com a URL de preview `https://6683466e-7bfb-49be-bb9e-7f5efdf9e30a.preview.emergentagent.com`); `frontend/.env` e `frontend/public/env-config.js` apontando para a mesma URL.
- Deps backend instaladas (`pip install --no-compile`), node_modules já presente.
- `mongorestore --drop` do backup `backup-20260905-155351.tar.gz` → 897 docs (usuarios 5, clientes 44, emprestimos 86).
- `./iniciar.sh restart` → mongodb/backend/frontend RUNNING; `/api/` 200; login inválido → 401 via UI.

## Setup realizado (06/2026)
- Criado `/app/backend/.env` com a env fornecida pelo usuário (MONGO_URL local, DB_NAME=gestorcred, JWT, EMERGENT_LLM_KEY, LOSDADOS, STRIPE test, etc).
- Criado `/app/frontend/.env` com `REACT_APP_BACKEND_URL` = URL de preview atual.
- Corrigido `/app/frontend/public/env-config.js` (runtime override) que apontava para host antigo `gestorcred-dev.preview...` → atualizado para a URL de preview atual. **Causa do "loading infinito" inicial.**
- Instaladas deps do backend (requirements sem re-resolver os pins conflitantes de emergentintegrations/litellm, ambos já presentes) e frontend (`yarn install`).
- Serviços via supervisor: mongodb, backend (8001), frontend (3000) — todos RUNNING.
- Banco importado via `mongorestore --drop` do backup do usuário: 897 documentos, coleções incl. usuarios(5), clientes(44), emprestimos(86). (parcelas/pagamentos vazios no backup.)

## Verificação
- Backend `/api/` → 200; `/api/assinaturas/planos` → 200; login inválido → 401.
- Frontend `/login` renderiza corretamente (página GestorCred).

## Observações / Backlog
- SMTP e webhooks (Stripe/MercadoPago) sem credenciais na .env — recursos de e-mail/pagamento ficam inativos até configurar.
- LOSDADOS e EMERGENT_LLM_KEY configurados (consultas/IA).
- Senhas dos usuários importados pertencem ao usuário; não foram alteradas.

## Auditoria de Segurança (07/09/2026)
Corrigidas e revalidadas (14/14 pytest via testing agent):
- CRÍTICO: webhook SyncPay (`/api/assinaturas/webhook-syncpay`) reconfirma a transação no gateway antes de liberar plano/crédito (antes: forjável, secret vazio → ativação grátis).
- ALTO: `admin/transacoes/cupom/{usar,validar}` agora exigem `require_admin` (antes públicos).
- MÉDIO: brute-force por IP (coleção `login_attempts_ip`, 20 falhas/janela → 30min) somado ao bloqueio por conta existente.
- BAIXO: CORS dev deriva de APP_URL.
Relatório completo: `/app/security_reports/AUDITORIA_SEGURANCA_2026-09.md`. Suite: `/app/backend/tests/test_security_audit.py`.
Admin (reset via scripts/seed_admin.py): diego.haidmann@gmail.com / Admin@2026.

## Segurança - Features (07/09/2026)
- Cloudflare Turnstile no cadastro: validado no backend (`services/turnstile_service.py`) em `/api/auth/registro`. Chaves de TESTE oficiais no env (backend `TURNSTILE_SECRET_KEY=1x00..AA`, frontend `REACT_APP_TURNSTILE_SITE_KEY=1x00..AA`). Widget no Login.js (aba Registro).
- Rate limit compartilhado: `security.py` RateLimiter agora é MongoDB-backed (`db.rate_limits`, janela fixa ip:bucket, TTL em expire_at) — compartilhado entre workers.
- Painel de Segurança admin: `/admin/seguranca` (rota `routes/seguranca.py`): contas/IPs bloqueados + webhooks suspeitos, auto-refresh 10s, botões de desbloqueio. Webhooks forjados são logados em `security_logs` (event_type=webhook_suspeito).
Validado testing agent iteration_51 (13/13). Chaves de teste Turnstile aceitam qualquer token; em produção trocar por chaves reais do dashboard Cloudflare.

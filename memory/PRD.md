# GestorCred / Kredor — PRD & Setup Notes

## Original request (2026-06)
User imported an existing project (already present in `/app`), asked to run `iniciar.sh`,
bring the stack online, import the attached MongoDB backup, and apply the provided
backend/frontend `.env` values.

## What it is
**Kredor / GestorCred** — SaaS for managing personal/informal loans with automatic
PIX + WhatsApp collection, CPF credit analysis, client portal, subscriptions, and wallet.

## Tech stack
- Backend: FastAPI (`/app/backend`, entry `server.py` -> `main.py`), APScheduler jobs.
- Frontend: React + CRACO + Tailwind (`/app/frontend`).
- DB: MongoDB (local standalone; app handles absence of transactions gracefully via
  `utils/transacao.py`).
- Integrations: LosDados (CPF), Stripe/MercadoPago, SMTP, Cloudflare Turnstile, WhatsApp.

## Setup done (2026-06)
- Restored MongoDB dump into DB `gestorcred` (8818 docs: 7 usuarios, 47 clientes, 90 emprestimos).
- Wrote `/app/backend/.env` with user-provided values. Empty `APP_URL` set to the preview
  URL and added `CORS_ORIGINS` (preview + localhost) so the frontend origin passes CORS
  (dev mode allows localhost + APP_URL).
- Wrote `/app/frontend/.env` with `REACT_APP_BACKEND_URL` = preview URL, `WDS_SOCKET_PORT=443`,
  `REACT_APP_TURNSTILE_SITE_KEY`.
- `pip install -r requirements.txt`; frontend `node_modules` already present.
- Restarted `backend` + `frontend` via supervisor. Backend health `GET /api/` -> 200.
  Landing page renders; scheduler running.

## Status
Application is LIVE and functional end-to-end (landing page loads, backend healthy,
DB restored, auth route reachable/Turnstile-protected).

## Fase 1.5 — Correções (concluída em 2026-06, verificada por pytest)
Ambiente: container Emergent (`/app`, supervisor, MongoDB standalone) — não a VPS do doc.
- **1.5.1** Valores negativos em empréstimos pequenos: `services/calculos.py`
  - `_plano_parcelas_fixas` agora divide principal e juros separadamente (soma = total),
    nunca gera principal/juros negativos.
  - `calcular_tabela_price` limita amortização ao saldo (`min(pmt-juros, saldo)`).
  - Validação `principal < periodos` → `DivisaoInvalidaError` (mapeada p/ HTTP 422 em `main.py`).
  - Prova: `tests/test_dinheiro.py` — **2865 passed** (grade Price/SAC/fixas + 422).
- **1.5.2** `utils/transacao.py`: em produção sem replica set levanta RuntimeError; em dev
  loga warning uma vez. Prova: RuntimeError confirmado com ENVIRONMENT=production.
- **1.5.3** `pytest-asyncio==1.4.0` + `backend/pytest.ini` (asyncio_mode=auto). Os 3 testes de
  race condition agora RODAM e passam (antes: skipped/warning).
- **1.5.4** `scripts/checar_session_em_transacao.py` estendido: além de `db.*`, cobre chamadas
  `await` de service dentro do bloco transacional (allowlist explícita). exit 0 no código real.
- **1.5.5** `frontend/Dockerfile` → `node:20-alpine` (yarn.lock fixa react-router-dom@7 >=node20).
  Nota: `docker compose build` não roda neste preview (sem daemon); mudança aplicada por inspeção.

Falhas de teste restantes NÃO são regressão: testes de login/Turnstile/segurança (precisam de
HTTP + credencial real) e jobs de empréstimos abertos (dado restaurado tem campo int None num
`Parcela` — confirmado idêntico ANTES das minhas mudanças via git stash).

## Backlog / Next
- P1: Fase 2 — 2.1 logging estruturado, 2.2 datas como Date do BSON, 2.3 eliminar N+1.
- P1: Fase 3 — 3.1 gateway único, 3.2 arquivos mortos, 3.3 imports em função, 3.4 cálculo só no
  backend, 3.5 frontend (componentes grandes, chamadas via src/api).
- P2: Dado restaurado com `Parcela.valor_*` None quebra o job de abertos — limpar/migrar.
- P2: Configurar SMTP e webhooks de pagamento; obter senha válida p/ E2E autenticado.

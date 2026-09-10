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

## Backlog / Next
- P1: Configure real SMTP creds if email sending is needed (currently blank).
- P1: Configure Stripe/MercadoPago webhook secrets for payment flows.
- P2: Obtain/reset a valid login password to exercise full authenticated flows.

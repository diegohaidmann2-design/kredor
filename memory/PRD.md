# GestorCred — PRD / Handoff

## Problem statement original
Importar projeto existente, rodar `iniciar.sh`, colocar tudo no ar, importar o banco anexado e usar a `.env` fornecida.

## Stack
- Backend: FastAPI (entry `server.py` → `main.py`), MongoDB (motor), APScheduler, emergentintegrations/litellm.
- Frontend: React (CRA), TailwindCSS, framer-motion, axios. Contextos: Auth, Portal, Theme.
- DB: MongoDB local, database `gestorcred`.

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

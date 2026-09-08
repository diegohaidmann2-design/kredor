# GestorCred — Import & Setup

## Problem Statement
Importar projeto existente (GestorCred - SaaS de gestão de empréstimos), rodar iniciar.sh, subir tudo no ar, importar banco anexado (backup-20260905-155351.tar.gz) e usar as .env fornecidas.

## Stack
- Backend: FastAPI (backend/main.py via server.py), MongoDB (motor), APScheduler
- Frontend: React 19 (CRACO), Tailwind, Radix UI
- DB: MongoDB local, database `gestorcred`

## Setup Done (2026-09-08)
- Criado /app/backend/.env com envs fornecidas (EMERGENT_LLM_KEY substituída pela chave real do ambiente; APP_URL preenchida com URL do preview)
- Criado /app/frontend/.env (REACT_APP_BACKEND_URL = URL do preview)
- Restaurado banco via mongorestore --db gestorcred --drop: 897 docs, 35 coleções (5 usuários, 44 clientes, 86 empréstimos)
- Dependências backend instaladas; frontend node_modules já presente
- Serviços backend+frontend reiniciados via supervisor; health-check OK (200)
- Landing page renderizando corretamente

## Notes
- Login dos usuários usa senhas hasheadas no backup restaurado (senhas originais não conhecidas)

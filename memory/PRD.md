# GestorCred — Projeto Importado

## Estado Atual (2026-06)
- Projeto existente importado e colocado no ar via supervisor (backend, frontend, mongodb).
- backend/.env e frontend/.env criados (estavam ausentes).
- Backend FastAPI (/app/backend, server:app :8001) — HTTP 200.
- Frontend React (/app/frontend :3000) — HTTP 200.
- MongoDB local, DB_NAME=gestorcred.

## Banco de Dados
- Restaurado a partir de backup-20260905-155351.tar.gz (mongodump).
- 897 documentos. usuarios: 5, clientes: 44, emprestimos: 86.
- parcelas e pagamentos vieram vazios no dump original.

## Stack
- FastAPI + Motor/MongoDB + APScheduler; React (CRA/CRACO) + Tailwind.

## Observacoes
- Login usa contas reais do dump (ex.: diego.haidmann@gmail.com). Senhas nao conhecidas.

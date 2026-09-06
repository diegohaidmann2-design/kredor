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

## Módulo CPF Premium (2026-06)
- Novo módulo de consulta "CPF Premium" (dossiê completo) via LosDados POST /cpf.
- Backend: services/losdados_service.consultar_cpf_premium; rota POST /api/consultas/cpf-premium (tipo 'cpf-premium'); preço padrão R$ 2,50 (consultas_precos); PDF do dossiê premium (consulta_pdf.py).
- Frontend: pages/Consultas.js — módulo 'CPF Premium' (ícone coroa), PremiumProfile/PremiumSecao/PremiumBloco renderizam foto, perfil e 40 seções (campos/tabela) expansíveis. api.js: consultasAPI.cpfPremium.
- Validado (iteration_48): backend 8/8, frontend 100%. Débito de R$2,50 na carteira, 402 sem saldo, 400 CPF inválido, histórico/PDF ok.

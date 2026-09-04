# GestorCred — Sistema de Gestão de Empréstimos a Juros

## Problem Statement (original)
"importei um projeto, rode o iniciar.sh e coloque tudo no ar e importe o banco anexado"
Usuário importou um projeto existente (GestorCred), pediu para colocar todos os serviços no ar e restaurar o backup do banco de dados anexado.

## Arquitetura
- Backend: FastAPI (backend/main.py, server.py) — rotas em /api, prefixo obrigatório
- Frontend: React (CRA + craco), config de ambiente runtime via public/env-config.js (window._env_)
- Banco: MongoDB local (DB_NAME=gestorcred)
- Scheduler de jobs (APScheduler), rate limiting, headers de segurança, logging estruturado

## Setup realizado (2026-09-04)
- Criado backend/.env (MONGO_URL local, DB_NAME=gestorcred, JWT, FIELD_ENCRYPTION_KEY, CORS com URL de preview, EMERGENT_LLM_KEY, STRIPE test key)
- Criado frontend/.env (REACT_APP_BACKEND_URL = URL de preview atual)
- Instalada dependência ausente do backend: bleach
- yarn install no frontend
- Restaurado backup (backup-20260902-182538) no banco `gestorcred` — 8459 documentos
- Corrigido public/env-config.js e frontend/public/index.html: window._env_ apontava para URL de preview ANTIGA (instant-launch-44), causando spinner infinito na landing page. Atualizado para a URL de preview atual + cache-bust.
- Serviços no ar via supervisor: mongodb, backend (8001), frontend (3000)

## Dados restaurados (contagens principais)
- usuarios: 4 | clientes: 43 | emprestimos: 81 | parcelas: 307 | pagamentos: 195
- portal_auth: 51 | whatsapp_templates: 12 | auditoria: 554 | jobs_execucoes: 6534
- Campos cpf_cnpj/telefone estão em texto plano (não criptografados no backup)

## Status
- Landing page: OK
- Login page: OK
- Backend API: OK (auth retorna 401 corretamente para credenciais inválidas)
- Banco importado: OK

## Observações / Backlog
- Não possuo as senhas dos usuários existentes (hash no banco). O usuário deve usar suas próprias credenciais.
- Integrações de pagamento (Stripe/MercadoPago/Asaas/SyncPay), SMTP e WhatsApp estão sem credenciais reais no .env (desativadas até configuração).
- FIELD_ENCRYPTION_KEY foi definida com um valor novo; dados atuais são texto plano, então não há impacto de decriptação.

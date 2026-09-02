# GestorCred — Sistema de Gestão de Empréstimos

## Contexto
Projeto existente (React + FastAPI + MongoDB) importado e colocado em execução no ambiente. O banco de dados foi restaurado a partir do backup anexado `backup-20260902-182538.tar.gz`.

## Problem Statement (original)
"importe um projeto, coloque para rodar e importe o banco anexado."

## O que foi feito (data: 2026)
- **Banco importado**: `mongorestore` do dump para a database `gestorcred` (8459 documentos: 43 clientes, 81 empréstimos, 307 parcelas, 195 pagamentos, 4 usuários, WhatsApp, checkout/transações, etc).
- **Configuração de ambiente**: criados `backend/.env` (MONGO_URL local, DB_NAME=gestorcred, JWT, FIELD_ENCRYPTION_KEY, EMERGENT_LLM_KEY, STRIPE_API_KEY=sk_test_emergent) e `frontend/.env` (REACT_APP_BACKEND_URL do preview).
- **Serviços**: backend (uvicorn/supervisor :8001) e frontend (:3000) rodando; health `/api/` = 200; login validado end-to-end.
- **Correções de lint (32 bloqueios pré-existentes)**: bare `except` → `except Exception`, imports/funções duplicadas, star import em `suporte.py`, chave `$ne` duplicada, bug de serialização de ObjectId no export de transações.
- **Object Storage (Emergent)**: `routes/upload.py` (anexos do chat de suporte) e importação de backup em `routes/backup.py` migrados de disco local para object storage (durável em produção); chamadas de rede envolvidas em `asyncio.to_thread`.
- **Fix regressão**: `/api/backup/listar` agora inclui backups importados no object storage (via `backup_logs`).

## Credenciais
- Admin: `diego.haidmann@gmail.com` / `Admin@2026` (senha redefinida nesta importação; a original era desconhecida). Ver `/app/memory/test_credentials.md`.

## Status de testes
- 23/23 casos de backend (pytest) passando: auth, listagem de clientes/empréstimos, parcelas, relatórios, admin transações, suporte, upload→object storage→serve. Fluxo de importação de backup validado (não destrutivo).

## Observações / Limitações
- Campos criptografados (ex.: CPF em `clientes`) foram gravados com a `FIELD_ENCRYPTION_KEY` original de produção, desconhecida. Com a chave de dev atual, esses campos podem não descriptografar corretamente. Se necessário, informar a chave original.
- Integrações de WhatsApp / Stripe / SMTP presentes mas sem credenciais reais (desativadas em dev).

## Backlog / Próximos passos (P1/P2)
- Validação de content-type por magic-bytes e limite de tamanho antes de bufferizar no upload (P2).
- Consolidar os dois endpoints de export em `admin_transacoes.py` (P2).
- Configurar credenciais reais de integrações quando o usuário fornecer (P1).

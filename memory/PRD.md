# GestorCred — Sistema de Gestão de Empréstimos a Juros

## Contexto
Projeto importado (existente). FastAPI (backend) + React 19 (frontend) + MongoDB.
Objetivo desta sessão: subir a aplicação no ar e restaurar o banco de dados anexado.

## Estado (2026-09-08)
- `.env` de backend e frontend criados com as variáveis fornecidas pelo usuário.
  - `DB_NAME=gestorcred`, `MONGO_URL=mongodb://localhost:27017`.
  - `REACT_APP_BACKEND_URL` e `APP_URL` apontam para o pod atual: https://b2965c15-d30b-426d-afbd-befcb996fcd6.preview.emergentagent.com (o APP_URL fornecido pelo usuário era de outro pod).
- Banco restaurado a partir de `backup-20260905-155351` via mongorestore (897 documentos, 0 falhas).
  - 5 usuários, 44 clientes, 86 empréstimos, 129 notificações, etc.
- Serviços rodando via supervisor: mongodb, backend (8001), frontend (3000). Backend `/api/` e `/health` respondem 200.
- Scheduler ativo (RUN_SCHEDULER=true), 15 jobs agendados.
- Landing page carrega corretamente.

## Observações
- Senhas dos usuários vêm do backup (hash), desconhecidas. Login requer credenciais originais ou reset.
- Integrações configuradas por env: EMERGENT_LLM_KEY, LosDados, Stripe (test), Turnstile (chave de teste). SMTP vazio (email desativado).

## Backlog / Next
- Validar fluxos de login/dashboard end-to-end com credenciais válidas.
- Configurar SMTP se envio de email for necessário.
- Configurar webhooks/secrets de pagamento (Stripe/MercadoPago) para produção.

# GestorCred — Sistema de Gestão de Empréstimos a Juros

## Problem Statement (original)
Importar projeto existente, rodar `iniciar.sh`, subir tudo no ar, importar o banco anexado (`backup-20260905-155351.tar.gz`) e usar a env fornecida pelo usuário.

## Stack
- Backend: FastAPI (`/app/backend`, entry `server.py` -> `main.py`), Motor/MongoDB, APScheduler (RUN_SCHEDULER=true).
- Frontend: React (CRA + craco), Tailwind, radix-ui.
- DB: MongoDB local (`mongodb://localhost:27017`), DB_NAME=`gestorcred`.
- Serviços via supervisor: mongodb, backend (8001), frontend (3000).

## Deploy status (2026-09-07)
- `.env` do backend criado com a env fornecida pelo usuário (APP_URL ajustado para o domínio de preview atual).
- `.env` do frontend criado: REACT_APP_BACKEND_URL = domínio de preview; REACT_APP_TURNSTILE_SITE_KEY = chave de teste Cloudflare (`1x00000000000000000000AA`) — necessária pois o backend tem TURNSTILE_SECRET_KEY de teste e exige token no login.
- Banco restaurado via mongorestore: 897 documentos, 26 coleções (5 usuários, 44 clientes, 86 empréstimos, etc.).
- Todos os serviços RUNNING; backend `/api/` 200, frontend 200.
- Login validado end-to-end (conta QA + Turnstile de teste).

## Contas
- QA (seed, tenant vazio): qa.teste@gestorcred.com / Teste@2026 (admin, enterprise).
- Usuários reais do backup (senhas do usuário, não alteradas): diego.haidmann@gmail.com (admin), adilsonsoares203, rogeriomoura504, fredrichuriel, janainadamascenofr.
- Dados (clientes/empréstimos) pertencem aos usuários reais (multi-tenant por usuario_id).

## Notas / Integrações
- LosDados API, Stripe (test), MercadoPago, SMTP (vazio), EMERGENT_LLM_KEY configurados via env.
- Turnstile em modo teste (widget sempre passa).

## Feature: Amortização + Incorporação de Juros (2026-09-07)
Escopo confirmado com o usuário: SOMENTE empréstimos "Sem Prazo / Apenas Juros" (sem_prazo=true, status ativo).
- Amortização de capital (já existia): melhorado o modal com campo "Novo capital" dinâmico (data-testid=amortizar-novo-capital). Endpoint POST /api/emprestimos/{id}/amortizar.
- NOVO: Incorporação de juros manual — usuário informa valor de juros a somar ao capital (novo = capital + valor). Opcional: baixar parcelas de juros em aberto e recalcular juros das próximas. NÃO conta como receita (valor_pago=0, tipo=incorporacao_juros). Endpoint POST /api/emprestimos/{id}/incorporar-juros. Model IncorporacaoJurosRequest.
- Frontend: botão "Incorporar Juros" (data-testid=incorporar-juros-btn) + modal (data-testid=incorporar-modal) em EmprestimoDetalhes.js; api.js emprestimosAPI.incorporarJuros.
- Estorno bloqueado para tipo=incorporacao_juros em routes/pagamentos.py.
- Validado: backend e2e + testing agent frontend 100%.
- Empréstimo de demo (tenant QA) p/ testes na UI: /emprestimos/3a7cab82-951e-42ba-b79e-b438e7d6bea5 (capital R$ 2.000).

## Backlog / Next
- P1: Reset de senha do admin real (diego) via `scripts/seed_admin.py` se precisar acessar os dados importados pela UI.
- P2: Configurar SMTP real para envio de e-mails.
- P2: Configurar chaves reais de Turnstile/Stripe/MercadoPago para produção.

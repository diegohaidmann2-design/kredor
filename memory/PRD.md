# GestorCred — PRD / Estado do Projeto

## Problema original
Usuário importou projeto existente (GestorCred: FastAPI + React + MongoDB — gestão de
empréstimos a juros). Pediu: rodar iniciar.sh, subir tudo, e importar o banco (backup mongodump).

## Arquitetura
- Backend: FastAPI (supervisor, porta 8001, prefixo /api). Entrada: backend/server.py -> main.py.
- Frontend: React/CRA+craco (porta 3000). URL do backend lida de window._env_ (public/env-config.js) com fallback process.env (src/config/env.js).
- DB: MongoDB local, base 'gestorcred'.
- Scheduler de jobs (APScheduler) ligado via RUN_SCHEDULER=true.

## URL do ambiente (IMPORTANTE)
- Este workspace é servido em: https://eed5ff5f-23ea-4562-ba84-3a4dded3560b.preview.emergentagent.com
- Confirmado via rota-marcador /api/__marker__ (só respondeu neste host + localhost).
- O host 6683466e-... que o usuário mencionou é OUTRO pod/ambiente (não editável aqui).
- backend/.env APP_URL, frontend/.env e public/env-config.js apontam todos para eed5ff5f.

## Feito (2026-09-07)
- Criados backend/.env e frontend/.env (não existiam; só havia .example).
- env-config.js corrigido (apontava para host antigo cred-system-test -> travava no splash).
- Backup restaurado em 'gestorcred': 5 usuarios, 44 clientes, 86 emprestimos (897 docs).
- Dependências backend instaladas (pip install -r requirements.txt).
- Cloudflare Turnstile: habilitado com chaves de TESTE (backend TURNSTILE_SECRET_KEY + frontend
  REACT_APP_TURNSTILE_SITE_KEY=1x00000000000000000000AA). Bug do widget que não aparecia: RESOLVIDO
  (faltava a site key no frontend). Verificado por testing agent (iteration_53) — login QA vai ao dashboard.
- Usuário QA de teste: qa.teste@gestorcred.com / Teste@2026 (scripts/seed_qa_user.py).

## Observações / Backlog
- Dados importados pertencem ao usuário real diego.haidmann@gmail.com (usuario_id fabf3ca4...).
  Para VER os dados, logar como Diego. Senha real é do usuário; se esquecida, rodar
  scripts/seed_admin.py define Admin@2026 (sobrescreve a senha do Diego).
- SMTP/Stripe/MercadoPago não configurados (vazios) — e-mail e pagamentos ficam inativos até ter chaves.
- LOSDADOS_API_KEY presente (consulta de CPF).

## Iterações de UI (2026-09-07)
- /admin/seguranca: alinhada ao visual do sistema (agora usa <Layout> com sidebar + tokens de tema).
  Botão "Atualizar" agora dá feedback (ícone gira, "Atualizando…" -> "Atualizado", timestamp atualiza).
- /emprestimos: tabela desktop mais responsiva — coluna "Ações" fixa à direita (sempre visível),
  padding reduzido (px-6->px-4), nomes de cliente truncados (max-w + tooltip). Cards no mobile mantidos.
- Todas verificadas pelo testing agent (iterations 54 e 55, 100%).
- Backup reimportado após teste (o testing agent havia reatribuído posse dos dados p/ QA); posse do Diego restaurada.

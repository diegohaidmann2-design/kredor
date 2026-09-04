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

## Módulo de Consultas (implementado 04/09/2026)
- Nova página `/consultas` (menu lateral "Consultas") com módulo CPF (CNPJ/Telefone/Nome = "Em breve").
- Integração LosDados: toda chamada no backend; chave em `LOSDADOS_API_KEY` (env), NUNCA exposta ao frontend; `signature`/`issuer` removidos das respostas.
- Backend: `services/losdados_service.py` (valida CPF, httpx) + `routes/consultas.py` (POST /api/consultas/cpf, GET /historico, GET /{id}, DELETE /{id}); histórico salvo por usuário na coleção `consultas`.
- Frontend: `pages/Consultas.js` usa `<Layout>` global (Sidebar+estrutura). Resultados redesenhados: hero de perfil + medidor de score, abas de categoria (Cadastral/Contatos/Financeiro/Patrimônio/Outros), cards de seção com ícones (lucide) e histórico lateral. Diretrizes salvas em `/app/design_guidelines.json` (seção "consultas").
- Correção importante: renderizadores recursivos convertidos em FUNÇÕES (não componentes JSX) para evitar recursão infinita do plugin visual-edits (componentes mutuamente recursivos travavam o build do App.js).
- Testado e2e (iteration_38.json): 100% backend+frontend, segurança da chave validada.
- Conta de teste: qa.consultas@teste.com / Teste@123 (email verificado, trial).

## Consultas — layout responsivo (04/09/2026)
- Resultados migrados para MASONRY (CSS multi-columns: columns-1 md:columns-2 2xl:columns-3; cards com break-inside-avoid) para preencher o espaço sem buracos verticais.
- Área de resultados agora em flex (conteúdo flex-1 + histórico lg:w-80 fixo), aproveitando telas largas.
- Mobile-first validado (iteration_39.json, 100%): 390px = coluna única, histórico abaixo, sem overflow horizontal; desktop 1920px = 3 colunas; Sidebar recolhe no mobile.

## Título dinâmico da aba + Expandir/Recolher tudo (04/09/2026)
- Novo `components/PageTitle.js`: define document.title por rota (ex.: "Consultas · GestorCred", "Portal do Cliente · GestorCred"); landing "/" mantém o título SEO longo. Montado em App.js dentro do BrowserRouter.
- /consultas: botão "Expandir tudo / Recolher tudo" (data-testid consulta-toggle-todas) abre/fecha todas as seções da categoria atual; InfoCard agora controlado (props open/onToggle); estado openSecoes por seção, refletido por categoria. Validado iteration_40.json (100%).

## Consultas — cards mais largos + metadados (04/09/2026)
- Cards de resultado: masonry mudou de contagem fixa (3 col ~300px) para largura mínima por coluna ('columns-1 md:columns-[24rem]') -> desktop 2 col ~426px, mobile 1 col ~358px.
- Grid interno de campos agora adaptativo (grid-cols auto-fit minmax(150px,1fr)) com min-w-0 + break-words + overflow-wrap:anywhere; prettify converte underscores em espaços. Fim das sobreposições de rótulo (ex.: CNH). Validado iteration_41.json (100%, 0 overlaps/0 overflow).
- Metadados: URLs canônica/OG/Twitter/sitemap/robots atualizadas de instant-launch-44 para o domínio de preview atual.

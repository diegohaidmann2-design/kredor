# GestorCred — PRD / Estado do Projeto

## Problema / Objetivo
Projeto importado pelo usuário. Tarefa: rodar `iniciar.sh`, colocar a aplicação no ar
e importar o banco de dados anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`), entrada `server.py` -> `main.py`, rotas em `/app/backend/routes`.
- Frontend: React (CRACO) em `/app/frontend`.
- Banco: MongoDB local (`mongodb://localhost:27017`, DB `gestorcred`).
- Serviços via supervisor: backend (8001), frontend (3000), mongodb.
- Integrações presentes: Emergent LLM key, LosDados, Stripe (test), MercadoPago, SMTP (vazio), WhatsApp.

## Feito (2026-06)
- Criados `backend/.env` (conforme fornecido pelo usuário) e `frontend/.env` (REACT_APP_BACKEND_URL = preview).
- Instalada dependência `bleach` que faltava (bloqueada por conflito de resolver no install completo).
- Backend e frontend no ar (HTTP 200). Landing page renderiza corretamente.
- Banco importado via `mongorestore --drop` do backup do usuário: 897 documentos.
  - usuarios: 5, clientes: 44, emprestimos: 86, configuracoes: 11.
  - parcelas/pagamentos: 0 (não existiam no backup).

## Backlog / Próximos passos
- Definir senha de acesso (senhas do backup são hashes desconhecidos).
- Configurar SMTP / gateways de pagamento se for necessário testar cobrança/e-mail.

## Feito (2026-06) — Logo + Demo + Domínio
- Domínio canônico atualizado para https://gestorcred.cloud em index.html (canonical, OG, JSON-LD), sitemap.xml (só páginas públicas) e robots.txt (Disallow área logada). env-config.js (API) mantido intacto.
- Logo profissional minimalista gerado (seta de crescimento + G). Fundo removido -> src/assets/logomark.png (transparente). Favicons/app-icons regenerados em public/.
- Logo aplicado no header da LandingPage, Footer, Sidebar e Login (tile branco).
- Nova seção de demonstração: /app/frontend/src/components/DemoShowcase.js
  - Tour interativo animado (auto-play) com telas: Dashboard, Empréstimos/Parcelas, Cobrança PIX/WhatsApp, Consulta de CPF, Portal do Cliente.
  - Toggle "Vídeo": player YouTube/Vimeo. Para ativar, editar a constante VIDEO_DEMO_URL no topo do DemoShowcase.js.
  - Seção id="demo", link "Demo" no menu e botão "Ver Demonstração" no hero.

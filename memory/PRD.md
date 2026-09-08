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

## Iteração — Bug Sidebar + SEO Landing (2026-09-08)
### Bug fix
- Sidebar: itens pai com submenu (WhatsApp, Empréstimos, Auditoria) agora NAVEGAM para a seção e ficam SELECIONADOS ao clicar (highlight verde/âmbar) além de expandir. `parentSelected = isSubmenuActive || isExpanded`. Verificado pelo testing agent (100%).

### SEO / Confiança (site público)
- Framework detectado: CRA (react-scripts 5.0.1) + CRACO, React 19, React Router 7, sem SSR; preview servido pelo dev server.
- P0.1 OG/Twitter/JSON-LD estáticos limpos em public/index.html (home). Prerender por rota: NÃO usado react-snap (incompat. React 19 + preview é dev). Recomendação: Worker Cloudflare no deploy.
- P0.2 removido SEOFooter (keyword stuffing/agiotagem/localizar devedores). grep agiot=0.
- P1.3 H1 único; title 58 chars. P1.4 avatares em arquivo + lazy. P1.5 rodapé de confiança + disclaimer + placeholders CNPJ. P1.6 robots limpo (origin). P1.7 sitemap sem /login.
- P2.8 trial padronizado 7 dias (DB + copy). P2.9 marca 'GestorCred' (grep 'Gestor Cred'=0). P2.10 JSON-LD Organization + SoftwareApplication + FAQ.

### Placeholders pendentes (preencher)
- {{RAZAO_SOCIAL_AQUI}}, {{CNPJ_AQUI}}, {{EMAIL_SUPORTE}} no Footer.js
- og-image-gestorcred.jpg (já existe 70KB) — validar 1200x630 real do produto
- robots.txt em produção: garantir que Cloudflare/edge não sobrescreva com content-signals

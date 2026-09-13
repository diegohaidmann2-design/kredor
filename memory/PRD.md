# Kredor / GestorCred — PRD & Log de Execução

## Problema / Contexto
SaaS de gestão de empréstimos e cobrança (PIX/WhatsApp) para **credores particulares** (Brasil).
Stack: FastAPI + React (CRA/craco) + MongoDB. Foco recente: **SEO da camada pública**
(landing pages) sem trocar de stack — renderização resolvida com SSG/prerender em React.

## Ambiente (preview)
- backend/.env: DB_NAME=gestorcred, MONGO_URL local (standalone, sem replica set).
- frontend/.env + public/env-config.js: REACT_APP_BACKEND_URL = https://kredor-deploy.preview.emergentagent.com
- Domínio de produção fixo em canonical/sitemap/schema: **kredor.com.br**.
- Banco restaurado do dump `backup-20260913-183507` (9000 docs).

## Personas
- Credor particular saindo da planilha/caderninho (público-alvo confirmado).

## Requisitos core (estáticos)
- Site público indexável (HTML real por rota), meta única, schema, sitemap correto.
- App logado permanece SPA e bloqueado no robots.

## Implementado
### 2026-09 — Importação e subida
- Repo `diegohaidmann2-design/kredor` sincronizado em /app; deps instaladas; serviços no ar.
- Banco importado (mongorestore --drop → gestorcred).
- Corrigido env-config.js (apontava p/ domínio antigo credito-app-12).

### 2026-09 — SEO Fase 1 (técnico)
- **Sitemap dinâmico** via FastAPI: `GET /api/sitemap.xml` (routes/seo.py), lastmod real,
  inclui blog_posts quando existir. Static public/sitemap.xml regenerado (21 URLs).
  nginx.conf: `location = /sitemap.xml` faz proxy p/ backend (produção).
- **JSON-LD por rota** (fonte única; schema estático removido de public/index.html):
  components/JsonLd.js + lib/seoSchema.js. Home: Organization, WebSite, SoftwareApplication
  (offers R$97/197/497 + aggregateRating 4.9), FAQPage. LPs: BreadcrumbList, SoftwareApplication,
  FAQPage. Validado no HTML prerenderizado (1 de cada, sem duplicação).
- **FAQ com schema** na Home (6 perguntas) e nas LPs; FAQ.js com FAQPage + Breadcrumb + useSeo.
- **prerender.js corrigido**: fallback SPA serve o index.html base em memória (parou o vazamento
  do schema do Home para as demais rotas).
- **Lazy-load** de imagens do DemoShowcase (Testimonials já tinha).
- Meta única por rota já existia (useSeo) — validado (title/description/canonical/OG).

### 2026-09 — SEO Fase 2 (novas LPs)
- 7 LPs novas (pages/landings/), com conteúdo próprio por keyword, via CommercialLanding:
  /software-para-emprestimos, /sistema-para-credores, /sistema-microcredito,
  /gestao-carteira-credito, /contratos-digitais-ccb, /emprestimo-particular-como-organizar,
  /consulta-cpf-credito (com ressalva: ferramenta é do credor, não do tomador).
- Adicionadas em App.js (rotas), prerender.js (ROUTES) e sitemap. Build prerenderiza 13 rotas OK.

## Backlog / próximas fases
### 2026-09 — SEO Fase 3 (blog, calculadora, WebP)
- **Blog** DB-backed: backend routes/blog.py (`/api/blog/posts`, `/api/blog/posts/{slug}`),
  seed scripts/seed_blog.py (5 artigos long-tail com link interno para as LPs). Frontend
  pages/Blog.js + pages/BlogPost.js (Article + Breadcrumb + Blog schema; .blog-content CSS).
  prerender.js injeta window.__PRERENDER__ (dados do blog) p/ evitar CORS no prerender —
  20 rotas prerenderizadas com conteúdo real (13 LP + calculadora + /blog + 5 posts).
- **Calculadora de juros** pública `/calculadora-de-juros` (Price, SAC, simples, composto)
  com tabela de amortização, via CommercialLanding (SEO+schema+FAQ). Indexável e com CTA.
- **WebP**: telas do demo convertidas p/ .webp (~50% menores); DemoShowcase com lazy-load.
- Sitemap dinâmico agora com 28 URLs (inclui /blog, /calculadora-de-juros e os 5 posts).

### Próximas
- Mais artigos (meta 30 do Bloco 6) + hub-and-spoke; /modelos e /glossario (programático).
- GA4 + eventos de conversão; /demonstracao indexável; /comecar (form curto).
- **Fora do código (usuário)**: toggle de bots de IA no painel Cloudflare; validar indexação no GSC;
  diretórios (Capterra/GetApp/B2B Stack) e backlinks.

## Notas
- Mongo standalone: E2E que exigem replicaSet=rs0 não rodam neste preview.
- Mudanças de SEO ficam "baked" no build de produção (prerender). No dev-server (preview),
  o schema é injetado client-side (Google executa JS).

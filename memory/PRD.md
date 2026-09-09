# GestorCred — PRD / Estado do Projeto

## Problema original
Importar projeto existente (GestorCred — gestão de empréstimos e cobrança PIX/WhatsApp),
subir todos os serviços via iniciar.sh e restaurar o banco de dados anexado.

## Arquitetura
- Backend: FastAPI (`/app/backend`, entrypoint `server.py` -> `main.py`), rotas em `/app/backend/routes`
- Frontend: React (`/app/frontend`)
- Banco: MongoDB local, DB `gestorcred`
- Scheduler habilitado (RUN_SCHEDULER=true)

## Feito (2026-09-08)
- Criados `backend/.env` e `frontend/.env` conforme env fornecido pelo usuário.
  - APP_URL e REACT_APP_BACKEND_URL preenchidos com a URL de preview do ambiente.
- Restaurado dump MongoDB do backup `backup-20260905-155351` no DB `gestorcred`
  (897 documentos, 0 falhas). Coleções: usuarios(5), clientes(44), emprestimos(86), etc.
- Instaladas dependências Python faltantes (bleach + requirements.txt).
- Serviços rodando: mongodb, backend (HTTP 200 em /api/), frontend (landing carrega).

## Observações
- Usuários vieram do backup de produção (campo `senha_hash`, `perfil`, `plano`). As senhas
  são as originais do backup — desconhecidas por nós. Se houver problema de login, resetar senha.

## Backlog / Próximos
- P2: Resetar senha de admin caso necessário.

## Sessão 2 (2026-09-08) — Ajustes na tela de Empréstimos
- Item 2 (feito e testado): coluna TAXA/PRAZO nos empréstimos SEM prazo agora mostra
  "🔄 Aberto" + a porcentagem de juros ("15% / mês" ou "5% / sem"). Desktop e mobile.
  Helper getTaxaSemPrazoLabel em Emprestimos.js.
- Fix defensivo: getTaxaComPrazoLabel evita render "null% / nullm" em registros legados.
- Item 1 (análise): as ações Prorrogar/Amortizar/Incorporar/Quitar Aberto são exclusivas
  de empréstimos sem_prazo/apenas_juros (backend valida e recusa outros). Não se aplicam
  ao HUDSON (juros_simples, prazo fixo), que já tem Pagar/Editar/Detalhes/PDF/Excluir.
- Senha de teste do admin diego.haidmann@gmail.com redefinida para Teste@2026 (ver test_credentials.md).

## Sessão 3 (2026-09-08) — Prorrogar empréstimos de PRAZO FIXO
- Feito e testado (testing agent 8/8 backend + frontend OK):
  - Backend: POST /api/emprestimos/{id}/prorrogar agora ramifica por metodo_calculo.
    Para métodos de prazo fixo (juros_simples/compostos/tabela_price/sac) chama
    _prorrogar_prazo_fixo (routes/emprestimos.py ~2657): mantém parcelas pagas,
    soft-deleta as em aberto e re-amortiza o SALDO de capital em (abertas + N) parcelas
    via gerar_parcelas_simulacao; atualiza total_parcelas, prazo e valor_total_com_juros.
    Branch legado 'apenas_juros' preservado (regressão OK).
  - Frontend (Emprestimos.js): opção 'Prorrogar Empréstimo' agora aparece para qualquer
    método (status ativo/inadimplente); modal com texto condicional (re-amortização vs apenas_juros).
- Teste E2E validado: pagamento -> prorrogação (parcelas recalculadas, pagas mantidas) -> quitação.
- Testes: /app/backend/tests/test_prorrogacao_prazo_fixo.py (criam/limpam dados próprios).

## Sessão 4 (2026-09-08) — Prévia + Histórico + Recibo de Prorrogação
- Feito e testado (testing agent: frontend 100%, pytest 5/5):
  - PRÉVIA: POST /api/emprestimos/{id}/prorrogar/preview (reusa _calcular_plano_prazo_fixo)
    mostra no modal o novo cronograma (parcelas + valor de cada + novo total com juros) antes de confirmar.
  - HISTÓRICO: cada prorrogação faz $push em emprestimo.historico_prorrogacoes (data, períodos,
    parcelas antes/depois, saldo, valor parcela). Exibido no modal Detalhes.
  - RECIBO: GET /{id}/recibo-prorrogacao/{prorrogacao_id} (PDF com novo cronograma) e
    POST .../whatsapp (envio via Evolution API — NÃO conectada neste ambiente: retorna erro amigável).
- Fix P0: adicionado `historico_prorrogacoes: List[dict]` ao model Emprestimo (response_model
  estava removendo o campo). Corrigido default para lista vazia (null quebrava o $push).
- Testes: /app/backend/tests/test_prorrogacao_melhorias.py (5/5).

## Sessão 5 (2026-06 / fork) — Setup do ambiente + conclusão do reposicionamento SEO
Ambiente:
- Recriados backend/.env e frontend/.env com a env fornecida (APP_URL e
  REACT_APP_BACKEND_URL apontando para a URL de preview deste pod).
- Instaladas dependências (pip requirements + yarn). Serviços rodando: backend HTTP 200 em /api/,
  frontend compila (só warnings de lint).
- ATENÇÃO: DB `gestorcred` está VAZIO neste pod (dados de forks anteriores não persistem).
  Nenhum arquivo de banco foi anexado neste run — import pendente até o usuário enviar o dump.

Conclusão da tarefa de reposicionamento (SPA CRA + CRACO, React 19):
- Fix de compilação: Precos.js importava de `../../components` (fora de src/) -> `../components`.
- Sitemap.xml: adicionadas as landings comerciais + /precos + /seguranca (sem /login).
- Footer.js: link "Segurança" -> /seguranca (era /privacidade); "Preços" -> /precos;
  adicionado selo "Dados criptografados" (ShieldCheck) — Pilar 5.
- Verificado já pronto de forks anteriores: 7 landings comerciais (1 H1 cada, title/description
  próprios via hook useSeo + CommercialLanding), JSON-LD Organization/SoftwareApplication/FAQPage,
  og/twitter estáticos no index.html, robots.txt sem conflito, frase institucional no footer,
  zero termos proibidos, zero "Gestor Cred" (com espaço), zero data:image.
- Pilar 3 (prerender por rota) NÃO implementado: react-snap é incompatível com React 19 e
  quebraria o build. OG da home já funciona via tags estáticas (curl confirma). Recomendação:
  Cloudflare Worker no deploy para injetar meta por rota.

Placeholders a preencher: {{RAZAO_SOCIAL_AQUI}}, {{CNPJ_AQUI}}, {{EMAIL_SUPORTE}} (Footer),
imagem OG real em https://gestorcred.cloud/og-image-gestorcred.jpg, redes sociais (sameAs / links do footer).

## Sessão 6 (2026-06 / fork) — Dados institucionais editáveis pelo painel
- Backend: adicionados `razao_social`, `cnpj`, `email_suporte`, `endereco` ao model LandingConfig
  (models/configuracao.py). Expostos no GET público /api/configuracoes/landing e salvos via
  PUT /api/configuracoes/landing (require_admin — usado pelo super admin no painel).
- Frontend: nova seção "Dados Institucionais" na aba Landing de Configuracoes.js (inputs
  razão social, CNPJ, e-mail de suporte, endereço). Salva junto com o resto da landing.
- Footer.js: agora consome esses campos do config (sem placeholders hardcoded). Linha
  institucional só aparece quando ao menos um campo estiver preenchido; e-mail de suporte
  também vira link no bloco da marca. Fallback do copyright: nome_empresa || 'GestorCred'.
- CORREÇÃO CRÍTICA: public/env-config.js apontava para outro pod
  (financial-portal-26.preview...) e window._env_ tem precedência sobre process.env em
  src/config/env.js — TODA chamada de API do browser ia para o backend errado. Corrigido para
  a URL deste pod e bump de cache (?v=20260908c em index.html).
- Testado E2E: seed admin -> login -> PUT institucional -> GET público -> rodapé renderiza os
  dados. Depois os campos foram limpos para começar em branco (super admin preenche no painel).

OBSERVAÇÃO (fora do escopo desta sessão): o hero da LandingPage ainda diz
"Consulta de CPF e localização de devedores" — termo próximo dos proibidos do Pilar 1.
Sugerir trocar por "validação de dados para análise de crédito" se o usuário quiser.

## Sessão 7 (2026-06 / fork) — Hero profissional + redes sociais no painel
- Hero (LandingPage.js): "localização de devedores" -> "validação de dados para análise de
  crédito ... conformidade LGPD"; "consultar devedores" -> "validar dados de clientes".
- Backend: adicionados social_facebook/instagram/linkedin/youtube ao LandingConfig.
- Painel: nova seção "Redes Sociais" na aba Landing de Configuracoes.js (URLs completas).
- Footer: socialLinks agora vêm do config (só renderiza os preenchidos; seção some se vazia).
  Logo já era o assets/logomark.png. Testado E2E (PUT -> footer renderiza ícones). Campos
  limpos depois para o super admin preencher com URLs reais.

## Sessão 8 (2026-06 / fork) — Imagem OG da marca
- Gerada capa OG 1200x630 (tema escuro, logomark esmeralda + wordmark GestorCred + tagline
  "Gestao de emprestimos e cobranca PIX/WhatsApp"). Gerada via image tool e finalizada com PIL
  (crop 1.9:1 + tagline limpa auto-ajustada). Salva em public/og-image-gestorcred.jpg (~72KB).
- index.html já apontava og:image e twitter:image para
  https://gestorcred.cloud/og-image-gestorcred.jpg (funciona no domínio de produção).
- Servida com 200 (image/jpeg) no preview.

## Sessão 9 (2026-06 / fork) — Banco restaurado
- Restaurado o dump anexado (backup-20260905-155351) com mongorestore --drop na base gestorcred:
  897 documentos, 0 falhas. Coleções: 5 usuários, 44 clientes, 86 empréstimos, 11 configurações.
- Backend lê os dados reais (GET /api/configuracoes/landing OK). A restauração dropou a coleção
  'configuracoes', então os campos institucionais/redes que eu havia adicionado voltaram a
  vazio/None (o super admin preenche pelo painel; o front trata campos ausentes).
- ATENÇÃO login: a senha do admin real (diego.haidmann@gmail.com) é a do dono (desconhecida);
  os valores de teste anteriores foram sobrescritos. Reset só sob pedido explícito.

## Sessão 10 (2026-06 / fork) — REBRAND COMPLETO GestorCred -> Kredor (domínio kredor.com.br)
- Código: substituídas TODAS as ocorrências (266) da marca antiga.
  Frontend (src+public): GestorCred/Gestor Cred -> Kredor; wordmarks em spans divididos
  colapsados para "Kredor"; gestorcred.cloud/.com.br -> kredor.com.br; bare lowercase
  gestorcred -> kredor (storage keys, cache SW, manifest, filenames).
  Backend (.py): só formas de exibição + domínio (GestorCred/Gestor Cred/domínios). NÃO
  alterei o bare lowercase 'gestorcred' no backend (é usado em DB_NAME fallback, canais de
  logger, paths de object storage e args de mongosh nos testes — mudaria quebraria).
- .env: SMTP_FROM_EMAIL -> noreply@kredor.com.br, SMTP_FROM_NAME -> Kredor. MANTIDOS
  DB_NAME=gestorcred, JWT_SECRET_KEY e FIELD_ENCRYPTION_KEY (mudar a encryption key tornaria
  os dados criptografados restaurados ilegíveis).
- Banco: deep-replace das formas de exibição/ domínio em todas as coleções (4 docs:
  notificacoes, configuracoes, configuracoes_sistema). nome_empresa='Kredor'. PRESERVADO
  smtp_user/smtp_from_email 'gestorcred@cobraplus.space' (é credencial de login SMTP real).
- Assets (gerados da nova logo anexada): logomark.png (marca K), favicons 16/32/48/ico/png,
  logo192/512, apple-touch-icon, icon-maskable-192/512, logo-kredor.jpg, e nova OG
  og-image-kredor.jpg (1200x630, fundo claro + wordmark). Removidos os assets/refs antigos
  (og-image-gestorcred.jpg, logo-gestorcred.jpg, icon-192/512.svg não referenciados).
- Verificado: 0 vestígios da marca antiga em código e em textos do banco; home e login exibem
  a marca Kredor; título/manifest/og apontam kredor.com.br.

## Sessão 11 (2026-06 / fork) — Overhaul da copy da landing + SEO
- Hero: badge "7 dias grátis · sem cartão"; H1 único "Gestão de empréstimos e cobrança
  automática no PIX e WhatsApp"; subtítulo novo; CTAs "Começar grátis"/"Ver demonstração";
  microcopy (7 dias / sem cartão / configure em minutos); provas: "500+ credores usando",
  "R$ 50M+ em carteira gerenciada", "99,9% de disponibilidade".
- 4 pilares reescritos (Cobrança PIX automática, Régua no WhatsApp, Análise de crédito com CPF,
  Portal do cliente). Nova faixa "Para quem é" com 5 chips.
- Demo: título "Veja o Kredor por dentro"; sub "Telas reais: dashboard, contratos, análise de
  crédito, simulação e relatórios"; aba CPF "Dossiê e score" -> "Análise e score de crédito".
- Funcionalidades: novo título/sub (mesmos 12 cards). "Por que escolher" reescrito para
  "Menos planilha, menos calote, mais controle" + 5 bullets de benefício novos.
- CTA final: "Comece a profissionalizar sua carteira hoje" + "Criar conta grátis".
- SEO: meta description atualizada. plano_trial_dias=7 em todas as configs (fim do "3 dias").
- E-mails/WhatsApp: marca já estava como Kredor (rebrand da sessão 10); 0 traços restantes.

---

## Sessão 2026-09-09 — Setup + Prerender SEO da Home

### Setup do projeto (feito)
- `.env` backend/frontend criadas com os valores fornecidos (APP_URL/REACT_APP_BACKEND_URL = URL do preview).
- Banco `gestorcred` restaurado via mongorestore (897 docs, 35 coleções: 5 usuários, 44 clientes, 86 empréstimos).
- Deps backend instaladas; serviços via supervisor OK (backend /api/ 200, frontend 200).

### Prerender / SEO (feito)
- **Mecanismo antes:** NÃO existia prerender. App é SPA CRA/craco — TODAS as rotas (home e landings) serviam o mesmo `index.html` com `<div id="root">` vazio. SEO era 100% client-side (`hooks/useSeo.js`).
- **Por que a home parecia pior:** `LandingPage` tinha spinner bloqueante (`if(loading) return <spinner>`) que substituía todo o conteúdo até a API `obterLanding()` responder; landings renderizam conteúdo imediatamente.
- **Implementado:**
  - Removido o gate de loading bloqueante da home (`src/pages/LandingPage.js`) → conteúdo existe no 1º render.
  - `frontend/scripts/prerender.js` (puppeteer-core): sobe servidor estático da `build/`, abre cada rota pública, rola a página (dispara `whileInView`), captura HTML final e grava `build/<rota>/index.html`.
  - Rotas prerenderizadas: `/`, `/sistema-gestao-emprestimos`, `/cobranca-whatsapp`, `/cobranca-pix`, `/controle-de-parcelas-e-juros`, `/gestao-de-clientes`.
  - `package.json`: `build` agora roda `craco build && node scripts/prerender.js` (+ `build:nossg` e `prerender`). Dep dev: `puppeteer-core`.
  - `frontend/Dockerfile`: instala `chromium` no stage builder (`PUPPETEER_EXECUTABLE_PATH=/usr/bin/chromium-browser`).
  - `index.js` mantém `createRoot` (re-render sobre markup prerenderizado → sem warning de hydration).
- **Verificado (build local + curl):** home (113KB) e landings com conteúdo real; `curl /` mostra hero/Funcionalidades/Planos + og:image no HTML bruto; landings com title/og:title/description/canonical únicos; sem `display:none`; sem spinner; og-image 1200x630 40KB.
- **CAVEAT:** o preview roda dev server (`yarn start`), então `curl <preview>/` ainda retorna o template vazio. O prerender só aparece no deploy Docker/nginx (produção). Verificado direto no artefato de build.

### Pendências/Backlog
- og:image por página é a genérica da marca (igual p/ todas). Futuro: og:image único por landing.
- Senhas dos usuários vieram do backup de produção (desconhecidas nesta sessão).

### OG por página + Sitemap/Robots (2026-09-09)
- 5 imagens OG únicas (1200x630, ~58KB) geradas via `scripts/gen_og.py` (PIL, texto nítido + logo/marca): `public/og-<slug>.jpg` para cada landing.
- `hooks/useSeo.js` agora aceita `image` → seta og:image (+width/height), twitter:image e twitter:card. `CommercialLanding` repassa `seo.image`; cada landing define seu `image`.
- Prerender embute o og:image correto no HTML bruto de cada landing (verificado). Home mantém a capa genérica da marca.
- `robots.txt` e `sitemap.xml` já existiam com todas as landings + institucionais; datas de `lastmod` atualizadas para 2026-09-09.

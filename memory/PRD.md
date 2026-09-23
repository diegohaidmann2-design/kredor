# Kredor / GestorCred — PRD

## Problema / Origem
App de gestão de empréstimos a juros clonado do repositório `diegohaidmann2-design/kredor`, rodando em modo desenvolvimento no preview Emergent. Stack: FastAPI + React (CRA/craco) + MongoDB.

## Ambiente
- Host atual do preview (este pod): `https://gestorcred-preview-3.preview.emergentagent.com`
- `REACT_APP_BACKEND_URL` (frontend/.env), `APP_URL` e `CORS_ORIGINS` (backend/.env) devem apontar para o host do pod atual. IMPORTANTE: o frontend/.env versionado no git traz `gestorcred-staging-2...`; ao reabrir o projeto num pod novo é preciso re-substituir pelo host do preview atual.
- DB: `gestorcred`.
- Storage: Emergent Object Storage (EMERGENT_LLM_KEY setado). NÃO possui API de delete (soft-delete no DB é a fonte da verdade).
- Turnstile: chaves de TESTE (site 1x...AA / secret 1x...AA) — widget passa sozinho.

## Personas
- Dono/credor (login) — gerencia clientes, empréstimos, cobranças, aprova cadastros.
- Cliente final (sem login) — preenche ficha pública, futuramente aceita empréstimo.

## Implementado (com datas)
- 2026-06: Clone + subida do app; correção de dependências (frontend: crypto-js, date-fns-tz, jspdf, jspdf-autotable, qrcode.react).
- 2026-06: Import do banco `gestorcred` a partir do backup.
- 2026-06: **Bug raiz (CORS/host):** app servido em `kredor-preview` mas `REACT_APP_BACKEND_URL`/`env-config.js` apontavam para outro host → CORS bloqueava as chamadas → toast "Não foi possível carregar configurações". Corrigido: frontend aponta para o host canônico (mesma origem) e CORS_ORIGINS inclui ambos os hosts. Service worker: env-config.js agora network-first + CACHE_NAME v1.0.1.
- 2026-06: **Melhorias no cadastro público:** validação Cloudflare Turnstile no `POST /cadastro-publico/solicitar/{token}` (frontend + backend); limpeza de anexos do storage ao rejeitar/excluir ficha (`delete_object` + `_apagar_anexos_storage`). TTL index de `rate_limits` já existia.
- Testado (testing_agent iteration_3): 10/10 backend + frontend OK.
- 2026-06 (sessão atual): Ajuste do domínio do preview no `.env` (front+back) — o frontend estava com `gestorcred-staging-2` e todas as chamadas de API caíam por CORS (login/dashboard quebrados). Corrigido para o host do pod atual; app 100% funcional de novo.
- 2026-06 (sessão atual): **Modal profissional de cobrança em /pagamentos.** O botão "Cobrar" (por parcela) agora abre um modal (`components/pagamentos/CobrancaModal.jsx`) com: seleção de modelo (auto-seed de templates de cobrança + opção "Mensagem padrão"), pré-visualização estilo WhatsApp com a mensagem final renderizada (dados reais da parcela) e botão de envio. Backend: `enviar-cobranca-parcela` aceita `template_id`; novo `GET .../preview`. Seed de usuários de teste executado (ver test_credentials.md).
- 2026-06 (sessão atual): **Import do banco real** a partir de `backup-20260920-233738.tar.gz` (mongodump do DB `kredor` remapeado para `gestorcred` com `--drop`). 9189 docs: 6 usuários reais + 3 de teste, 48 clientes, 91 empréstimos, 333 parcelas, 216 pagamentos, 18 templates WhatsApp.
- 2026-06 (sessão atual): **Correção de CORS no login (multi-domínio).** O pod responde por dois hosts de preview (`58322996-...` e `gestorcred-staging-2`). O frontend fixava a API no host errado -> preflight bloqueado. Fix: `REACT_APP_BACKEND_URL` vazio no `frontend/.env` (env.js cai para `window.location.origin` = same-origin em qualquer host) + ambos os domínios no `CORS_ORIGINS`. Verificado pelo testing_agent (iteration_5): login 200 same-origin, sem erros de CORS.
- 2026-06 (sessão atual): **Redesign da página /notificacoes** (`pages/Notificacoes.js`) para remover a estética "cara de IA": trocados TODOS os emojis (🔔📩📅⚠️) e SVGs inline por ícones lucide-react; cards de resumo com chips de ícone + hover; filtros segmentados; linhas com chip colorido por tipo, barra de acento em não-lidas, badges e micro-animações (framer-motion, stagger + AnimatePresence); estado vazio e caixa "Como funcionam" refeitos no padrão da marca (esmeralda + Space Grotesk). Lógica/handlers/testids/API preservados; interações (filtro, marcar como lida) verificadas por screenshot.
- 2026-06 (sessão atual): **Correção crítica no /exportacao.** Bug: `routes/exportacao.py` gerava CSV com `csv.DictWriter(fieldnames=registros[0].keys())` — como os docs do Mongo têm campos heterogêneos, o `writerows` lançava ValueError -> HTTP 500, quebrando o CSV (formato padrão) para qualquer usuário com dados reais, além de omitir colunas. Fix: helper `_registros_para_csv_bytes()` monta o cabeçalho como UNIÃO de todas as chaves (ordem de aparição), serializa dict/list como JSON e normaliza None. JSON usa `default=str`. Verificado pelo testing_agent (iteration_6): backend 4/4 pytest + frontend Playwright OK (CSV 4 entidades -> 200 zip; CSV único -> 200 com todas as colunas; JSON -> 200). Também: `btn-exportar` passou a usar a prop `testId` (Button não encaminha `data-testid`). COBERTURA: exporta as 4 entidades de negócio (clientes, emprestimos, pagamentos, parcelas) com todas as colunas; NÃO inclui contratos/consultas/carteira/notificações/templates (candidato a expansão). Filtro de data só se aplica a emprestimos/pagamentos.

## Backlog / P0-P2
- P1: **Aceite de empréstimo reaproveitando a ficha pública** (assinatura + termos do contrato/CCB). Proposta definida; aguardando escolha de escopo do usuário.
- P2: Alinhar APP_URL ao host canônico (hoje é sobrescrito pelo supervisor com o alias; links de cadastro usam o alias, mas o preview canonicaliza no navegador).
- P2: Refatorar `cadastro_publico.py` (público vs admin) e inicializar `_arquivos_pendentes = {}` no topo.
- P2: Testar fluxo do DONO (aprovar/rejeitar) — precisa de credenciais de login (senhas do backup são desconhecidas).

## Próximas tarefas
1. Confirmar escopo do aceite de empréstimo e implementar.
2. (Se necessário) resetar senha de uma conta para permitir login/testes do lado dono.

---
## Atualização 2026-09-23
- Restaurado banco do backup `backup-20260917-020829` (mongodump `kredor` → DB `gestorcred`, 9115 docs).
- ENV do preview alinhada ao domínio `cred-sistema-preview.preview.emergentagent.com` (REACT_APP_BACKEND_URL, APP_URL, CORS_ORIGINS).
- Redesign do modal de detalhe/registro de pagamento em `frontend/src/components/pagamentos/PagamentoDetalheModal.jsx` (estilo Rocket Money adaptado ao tema escuro Kredor): valor em destaque, composição do valor, rodapé "statement", método por botões e ação clara "Confirmar pagamento". Integrado em `pages/Pagamentos.js`.
- Validado ponta a ponta: registrar pagamento parcial funciona e atualiza totais.

## Atualização 2026-09-23 (redesign agência /pagamentos)
- design_agent gerou /app/design_guidelines.json (tema escuro/esmeralda, fontes Cabinet Grotesk + Satoshi + JetBrains Mono, remoção de AI-slop).
- Fontes adicionadas em index.css (Fontshare) e tailwind.config.js (font-cabinet, font-satoshi), escopadas à área de Pagamentos.
- Refatoração visual completa de pages/Pagamentos.js e components/pagamentos/PagamentoDetalheModal.jsx: sem emojis (ícones lucide), sem badge soup (status = dot + texto), radii padronizados (rounded-xl/rounded-md), KPIs planos com ring, tabs underline, filtros minimalistas, linhas planas, valores em mono, barra flutuante de cobrança em massa, empty states com ícone lucide.
- Testado (iteration_7.json): 100% frontend (7/7 fluxos), sem regressões, todos os data-testid preservados. Modal com role=dialog/aria-modal.

## Atualização 2026-09-23 (4 melhorias pós-redesign)
1. Modal de parcela ganhou seção AÇÕES (Rocket Money): "Cobrar no WhatsApp", "Ver histórico" (lista de pagamentos da parcela) e "Recibo" por pagamento. Props novas em PagamentoDetalheModal: onCobrar, historico, onRecibo. Recibo confirmado (endpoint /pagamentos/{id}/recibo → 200 application/pdf).
2. Consistência visual aplicada a Dashboard.js e Agenda.js: fontes Cabinet/Satoshi, valores em JetBrains Mono, dots de status, remoção de emojis.
3. Clique na linha inteira da parcela abre o modal (data-testid parcela-row-<id>, role=button + Enter/Space); botões internos com stopPropagation.
4. KPIs com count-up (novo componente components/AnimatedNumber.jsx) e chip de variação vs mês anterior no card "Total recebido" (data-testid total-recebido-card-delta).
- Testado (iteration_8.json): ~95%, 7/7 fluxos primários PASS, sem regressões. Recibo PDF verificado via curl.

## 2026-09-23 — Redesign expandido (design de /pagamentos)
- Criado UI kit compartilhado: frontend/src/components/uikit.js (PageHeader, KpiCard, EmptyState, SearchBar, UnderlineTabs, PageShell).
- Aplicado o design da tela Pagamentos (font-cabinet black nos títulos, font-satoshi, cards rounded-xl com ring-1 ring-border, acento esmeralda, números mono, busca com border-b, tabs underline, EmptyState) em: Dashboard, Minha Equipe, Clientes, Cadastros & Aprovações, Empréstimos.
- Mudanças puramente visuais; lógica inalterada. Regressão frontend 100% (iteration_10.json), sem erros de console.
- Correção: btn-novo-emprestimo agora usa prop `testId` (Button.js não faz spread de props).
- Nota técnica: src/components/Button.js só aceita `testId` (não faz spread) — usar testId= em vez de data-testid= nesse componente.

## 2026-09-23 — Refinamentos do redesign (tabelas, KPIs, modais, tema claro)
- Empréstimos: KPIs no topo (Total emprestado destacado, Ativos, Em atraso) no padrão Dashboard/Pagamentos (uikit.KpiCard).
- Tabelas de Clientes e Empréstimos: avatar circular esmeralda com inicial, hover bg-muted/40, cabeçalho com border-b.
- Modais (Novo Cliente, Detalhes Cliente, Novo Empréstimo): título font-cabinet black, container rounded-2xl + ring-1 ring-border + shadow-2xl.
- Tema claro afinado (index.css .light): fundo off-white (210 20% 98%), cards brancos que destacam com ring-border, muted/border ajustados para melhor contraste.
- Verificado por screenshots em dark e light com dados de teste (3 clientes + 2 empréstimos na conta pro@kredorteste.com).

## 2026-09-23 — /clientes responsivo + análise de design
- /clientes: tabela desktop agora `w-full` (sem overflow-x-auto), colunas Nome/Email truncadas; mobile em cards. Sem scroll horizontal (verificado 1920/1366/390).
- Análise de design (design_agent) gerou /app/design_guidelines.json. Principal "rastro de IA": emojis em formulários/tabelas e badges genéricos.
- Quick wins aplicados: removidos todos os emojis (📅📆🗓️🔄💡⚡⚠️ℹ️) do NovoEmprestimoModal e da tabela de Empréstimos; valores monetários em fonte mono.
- Backlog do blueprint (não aplicado ainda): badges neo-brutalistas (rounded-md, ring-1, uppercase, dot), números à direita em colunas numéricas, modal detalhes do cliente redesenhado, role='dialog' no NovoEmprestimoModal.

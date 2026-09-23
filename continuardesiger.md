# Continuar Design — Kredor

Roadmap para **remover o "rastro de IA"** e **aplicar o novo visual** (referência: tela `/pagamentos`) em todo o sistema.

> Fonte da verdade dos tokens/regras: `/app/design_guidelines.json`
> Kit compartilhado já criado: `/app/frontend/src/components/uikit.js`

---

## 0. Estado atual

### ✅ Já redesenhado (referência + concluído)
- `pages/Pagamentos.js` — **tela de referência aprovada**
- `pages/Dashboard.js`, `pages/Clientes.js`, `pages/Equipe.js`, `pages/Aprovacoes.js`, `pages/Emprestimos.js`
- `components/uikit.js` — `PageHeader`, `KpiCard`, `EmptyState`, `SearchBar`, `UnderlineTabs`, `PageShell`
- Tema claro afinado em `index.css`
- Emojis já removidos de: `NovoEmprestimoModal.js` e tabela de `Emprestimos.js`

### 🔢 Dívida de design (números da auditoria)
- **~350 emojis** em **~40 arquivos** (maiores ofensores abaixo)
- **83** usos de `rounded-full` (badges/pills genéricos de status)
- **45** arquivos com `shadow-lg/xl/md` (sombras genéricas — trocar por `ring-1 ring-border`)
- **~40 páginas** com títulos antigos (`text-2xl/3xl font-bold` / `font-display font-bold`) → migrar para `PageHeader` (font-cabinet black)
- `pages/Perfil.js` ainda usa o componente `<Header>` antigo

---

## 1. Regras do novo visual (checklist por elemento)

Aplicar SEM quebrar funcionalidade. Regras derivadas de `design_guidelines.json`:

1. **Emojis → ícones Lucide** monocromáticos. Nenhum emoji em labels, selects, botões, badges, toasts, nav.
2. **Títulos de página** → `PageHeader` do uikit (`font-cabinet font-black tracking-tighter`) dentro de `container mx-auto px-4 sm:px-6 py-8 font-satoshi`.
3. **KPIs / cards de métrica** → `KpiCard` do uikit (`rounded-xl bg-card ring-1 ring-border p-6`, rótulo uppercase tracking largo, número em `font-mono`, ícone lucide no topo-direito, hover `-translate-y-px`).
4. **Badges de status → neo-brutalista**: `rounded-md ring-1 ring-inset uppercase tracking-wider text-xs`, com **ponto colorido** antes do texto. Nada de `rounded-full` chapado.
   - success: `bg-emerald-500/10 text-emerald-500 ring-emerald-500/20`
   - warning: `bg-amber-500/10 text-amber-500 ring-amber-500/20`
   - danger: `bg-rose-500/10 text-rose-500 ring-rose-500/20`
   - info: `bg-blue-500/10 text-blue-500 ring-blue-500/20`
   - neutral: `bg-slate-500/10 text-slate-400 ring-slate-500/20`
5. **Superfícies** → trocar `shadow-lg/xl` por `ring-1 ring-border`. Modais/dropdowns: `ring-1 ring-border` + `backdrop-blur-xl` (fundo sólido, nunca transparente).
6. **Tabelas densas**:
   - Desktop: `w-full` (sem `overflow-x-auto`), `truncate`/`max-w` em nome/email, avatar circular esmeralda com inicial.
   - Números em `font-mono` **alinhados à direita** (header + célula).
   - Mobile: esconder `<table>` (`hidden md:table`) e mostrar **cards empilhados** (`grid md:hidden gap-4`).
7. **Busca** → minimalista: só borda inferior (`border-b bg-transparent`), `focus:border-emerald-500`.
8. **Empty states** → `EmptyState` do uikit (ícone lucide tênue + título Cabinet + texto Satoshi).
9. **Abas** → sublinhado esmeralda animado (`UnderlineTabs` ou `framer-motion layoutId`).
10. **Botões** → CTA esmeralda consistente; hover por propriedade específica (nunca `transition: all`).
11. **Tema claro/escuro** → sempre via classes semânticas Tailwind (`bg-card`, `text-foreground`, `border-border`), testar nos dois temas.

---

## 2. Componentes compartilhados a criar/estender no `uikit.js`

Construir uma vez, reusar em tudo (reduz retrabalho por página):

- [ ] **`StatusBadge`** — recebe `status` + mapa de tom; renderiza badge neo-brutalista com ponto. Substitui os 83 `rounded-full`.
- [ ] **`Avatar`** — círculo com inicial; cor derivada do nome (hash → paleta), fonte mono. Usar em todas as listas.
- [ ] **`DataTable`** (ou padrão documentado) — tabela responsiva: desktop `w-full` + mobile cards automáticos, colunas com alinhamento/`truncate`.
- [ ] **`Modal`** (shell) — overlay `bg-background/70 backdrop-blur-sm`, painel `rounded-2xl ring-1 ring-border shadow-2xl`, título `font-cabinet font-black`, botão fechar padrão. Padroniza todos os modais.
- [ ] **`SectionCard`** — card de seção `rounded-xl bg-card ring-1 ring-border p-6` (substitui cards com shadow).
- [ ] **`FormField`** — label + input/select minimalista padronizado (foco esmeralda), sem emojis.

---

## 3. Plano por fases (prioridade)

### 🔴 FASE 1 — Componentes globais (impacto em todas as telas)
Estes aparecem em quase todas as páginas; corrigir primeiro dá ganho imediato.
- [ ] `components/Sidebar.js` — aplicar visual novo; remover emojis `🆕` (badge "novo") e `👑` (admin) → ícones Lucide (`Sparkles`, `Crown`).
- [ ] `components/Header.js` — alinhar ao `PageHeader` ou aposentar (migrar `Perfil.js`).
- [ ] `App.js` — remover 16 emojis (badges `🆕` nas rotas/nav, `🔒`, `⚠️`).
- [ ] `components/ScoreBadge.js` — trocar `🟢🔵🟡🟠🔴` por ponto colorido + Lucide.
- [ ] `components/NotificationBell.js`, `components/BannerTrialExpirando.js` — ícones Lucide, badge neo-brutalista.
- [ ] `components/OnboardingChecklist.js` (10 emojis), `OnboardingWelcomeModal.js` (🎉), `DemoShowcase.js`, `Testimonials.js` (💬), `PagamentosPendentesSection.js` (🎉).
- [ ] Criar os componentes da Seção 2 no `uikit.js`.

### 🔴 FASE 2 — Núcleo do fluxo de empréstimos (mais usado no dia a dia)
- [ ] `components/emprestimos/DetalhesEmprestimoModal.js` — emojis (`✅✓⚠️📅🚨💰→`), aplicar Modal shell + badges.
- [ ] `components/emprestimos/PagamentosDoEmprestimo.js` — 8 emojis (`🧾📄🔢📅💵💰🤝`) → Lucide.
- [ ] `pages/EmprestimoDetalhes.js` — header, badges, cards, mono nos valores.
- [ ] `pages/EmprestimosAbertos.js` — mesmo padrão de `Emprestimos.js` (KPIs + tabela + avatar).
- [ ] `pages/Contratos.js` (22 emojis) — passos/checklist com Lucide, cards ring-1.
- [ ] `pages/ReguaCobranca.js`, `pages/Agenda.js`, `pages/Consultas.js`.

### 🟡 FASE 3 — Analytics, config e comunicação
- [ ] `pages/Relatorios.js`, `pages/AnaliseDashboard.js`, `pages/AnaliseClientes.js` (12 emojis) — KPIs + gráficos no padrão.
- [ ] `pages/Carteira.js`, `pages/Exportacao.js`, `pages/Auditoria.js`, `pages/Notificacoes.js`.
- [ ] `pages/Configuracoes.js` (**69 emojis** — maior ofensor), `pages/ConfigNotificacoes.js` (44), `pages/Perfil.js`, `pages/Seguranca.js`.
- [ ] `pages/Simulacao.js`, `pages/AssistenteIA.js`.
- [ ] WhatsApp: `WhatsAppConfig.js` (13), `WhatsAppLogs.js`, `WhatsAppTemplates.js`, `WhatsAppAntiSpam.js` (7).
- [ ] `pages/Assinatura.js`, `pages/AssinaturaExpirada.js` (💚).

### 🟡 FASE 4 — Portal do cliente + Admin
- [ ] `pages/Portal/*` (PortalDashboard 5 emojis, PortalEmprestimo) — aplicar visual (contexto do cliente final).
- [ ] Admin: `AdminUsuarios.js` (👑🔐⚠️), `AdminScheduler.js` (11), `AdminAssinaturas`, `AdminTransacoes`, `AdminCarteiras`, `AdminCupons`, `AdminBackup`, `AdminSeguranca`, `AdminSuporte(+Detalhes)`, `SuperAdmin`.

### 🟢 FASE 5 — Público / checkout / autenticação
- [ ] `pages/Login.js`, `pages/Verify2FA.js`, `pages/VerificarEmail.js` (5), `pages/AceitarConvite.js`, `pages/AceiteEmprestimo.js`.
- [ ] `pages/CadastroPublico.js` (🎉✕), `pages/Simulacao.js`.
- [ ] Checkout: `CheckoutAsaasPagamento.js`, `CheckoutTransparenteBrick.js` (6), `CheckoutSyncPayPagamento.js`, `CheckoutPublico.js` — manter confiança visual + brand.

### 🟢 FASE 6 — Marketing / institucional (estética própria, mas sem emojis soltos e coerente com a marca)
- [ ] `LandingPage.js`, `Precos.js`, `Sobre.js`, `ComoFunciona.js`, `FAQ.js`, `Contato.js`, `Blog.js`, `BlogPost.js`, `PoliticaPrivacidade.js`, `TermosUso.js`, `landings/*` (13 páginas).

### 🧹 Limpeza
- [ ] `pages/TimezoneTest.js` — página de debug (🌍📱🖥️❌🔄✅). Remover do build de produção ou isolar.

---

## 4. Ordem de execução sugerida (para o próximo agente/sessão)
1. Construir componentes do uikit (Seção 2). — desbloqueia todo o resto.
2. FASE 1 (globais) → maior impacto visual imediato.
3. FASE 2 (fluxo de empréstimos) → é o coração do produto.
4. Seguir Fases 3→6.
5. Após cada fase: rodar `testing_agent` (frontend) validando que telas abrem, sem scroll horizontal, sem emojis, sem erros de console, nos temas claro e escuro.

## 5. Definição de "pronto" por tela
- [ ] Sem emojis (só ícones Lucide)
- [ ] Título via `PageHeader` (font-cabinet)
- [ ] Cards `ring-1 ring-border` (sem shadow genérica)
- [ ] Badges neo-brutalistas com ponto
- [ ] Tabelas responsivas (desktop `w-full` + mobile cards), números mono à direita
- [ ] Busca/inputs minimalistas
- [ ] Empty states via `EmptyState`
- [ ] Modais no shell padrão
- [ ] Funciona em tema claro e escuro
- [ ] `data-testid` em todos os elementos interativos

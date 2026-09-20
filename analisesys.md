# Análise Competitiva — SysJuros

> Benchmarking técnico e funcional executado com acesso autenticado real à plataforma
> `https://sysjuros.com.br` via automação de navegador (Chromium + Playwright).
> Evidências capturadas em `/app/bench/out/` (screenshots + dumps de texto/rede).
> **Nota de segurança:** nenhuma credencial foi gravada neste relatório, em logs ou screenshots.
> Nenhuma transação financeira real foi executada. Nenhum dado real de terceiros foi acessado.
> Os testes de cálculo foram feitos **sem salvar** contratos (leitura dos campos calculados ao vivo).

---

## 1. Resumo Executivo

O **SysJuros** é um SaaS brasileiro de **gestão de empréstimos e cobranças** (nicho de credores
informais / microcrédito / "contas a receber"), construído **inteiramente no Bubble.io** (no-code).
Proposta: substituir "caderninho de papel" e planilhas por um controle simples de clientes,
contratos, parcelas e recebimentos, com forte apelo **mobile** e preço agressivo (**R$ 37/mês**).

Principais conclusões:

- **Motor financeiro simples e transparente**, do tipo **juros flat / add-on** (markup fixo sobre o
  principal), **não PRICE nem SAC**. Isso o torna fácil de usar, mas limitado para cenários formais.
- **Dois tipos de contrato:** *Fixo* (dívida rotativa "só juros" com pagamento mínimo) e
  *Parcelado* (parcelas iguais = total a receber ÷ nº de parcelas).
- **Frequências:** Diário, Semanal, Quinzenal, Mensal — com regras de dias (úteis, seg-sex, todos).
- **Arquitetura Bubble** limita a performance, o SEO e a extensibilidade — **grande oportunidade
  competitiva** para o nosso GestorCred (React SSR/prerender + backend próprio).
- **SEO fraquíssimo**: 1 landing, sem sitemap, sem meta description, sem canonical, sem schema.org.
- **Ausências relevantes** (não localizadas na conta): integração de cobrança WhatsApp/PIX ativa,
  emissão de CCB/contrato digital, consulta de CPF, régua de cobrança automatizada, exportações.

**Veredito estratégico:** o SysJuros vence em **simplicidade e preço**. Podemos superá-lo com
**motor financeiro correto (PRICE/SAC + IOF/CET)**, **cobrança automatizada (WhatsApp/PIX)**,
**consulta de CPF** e **SEO real** — mantendo a simplicidade de uso.

---

## 2. Mapa Completo da Plataforma

```
Landing (sysjuros.com.br)  → Bubble, CSR, 1 página + FAQ + planos
   ↓  /auth/log-in
Área autenticada (/web/*)
   ├── /web/dashboard   → Início (KPIs do mês)
   ├── /web/customer    → Clientes
   ├── /web/contract    → Contratos (Fixo | Parcelado)
   ├── /web/salaries    → Vencimentos (parcelas a receber/atrasadas/recebidas)
   ├── /web/reports     → Relatórios (Evolução gráficos, Rentabilidade; 2 "Em breve")
   ├── /web/settings    → Configurações (Perfil | Plano | Notificação)
   ├── Como usar        → (ajuda/onboarding)
   └── Suporte          → (canal de suporte)
```

Menu lateral fixo (perfil "Administrador"). Navegação por workflows Bubble (sem `<a href>`).

---

## 3. Funcionalidades Encontradas

| Módulo | Funcionalidade | Como funciona | Evidência | Oportunidade |
|---|---|---|---|---|
| Auth | Login e-mail/senha | Form Bubble, cria cookie `sysjuros_live_u2main`; redireciona p/ `/web/dashboard` | `00_login.png`, `session.txt` | Já temos JWT; ok |
| Dashboard | KPIs do mês | Total em aberto, Recebido hoje/ontem, Custos, Entradas, A receber, Rentabilidade (Recebido−Custo), Novos contratos/clientes | `01_after_login.txt` | Superável c/ gráficos e metas |
| Clientes | Cadastro | Nome, Telefone (+flag Exterior), Email, Nascimento, CPF/CNPJ, RG, Endereço (CEP→auto), UF | `21_customer_form.txt` | Add consulta CPF, WhatsApp, score |
| Contratos | Contrato Fixo | Custo + Taxa% → Total = Custo×(1+i); Pagamento mínimo (juro periódico) | `43_fixo_1000_taxa10.png` | Add PRICE/SAC/CET |
| Contratos | Contrato Parcelado | Custo + Valor a receber → parcelas iguais = total/n; freq. D/S/Q/M | `42_parc_1000_1300_3x.png` | Add amortização real |
| Vencimentos | Painel de parcelas | Cards: Vencem hoje, Atrasadas, A receber, Recebidas; abas Todos/Pagos/Não pagos; filtro por período; totais | `10_Vencimentos.txt` | Add baixa em massa, PIX |
| Relatórios | Evolução (gráficos) | Clientes, contratos, valor contratado e recebimentos — últimos 12 meses | `10_Relatorios.txt` | Add export CSV/PDF |
| Relatórios | Rentabilidade contratos | Custo, recebido, saldo em aberto, capital exposto, margem por contrato | `10_Relatorios.txt` | Superável c/ DRE/fluxo caixa |
| Relatórios | Projetado×Realizado / Custo×Recebido | "Em breve" (não implementado) | `10_Relatorios.txt` | Entregar antes deles |
| Config | Perfil / Plano / Notificação | Foto, Nome, Telefone, Nascimento; abas Plano e Notificação | `10_Configuracoes.txt` | — |

---

## 4. Clientes / Devedores

**Rota:** `/web/customer` — Evidência: `21_customer_form.txt`, `10_Clientes.txt`.

Formulário "Novo cliente" (modal), campos observados:

- **Identificação:** Nome (primeiro nome + sobrenome), Telefone (`tel`, máscara `99 9 9999-9999`),
  checkbox **Exterior** (telefone internacional), Email, Nascimento, **CPF/CNPJ**, **RG**.
- **Endereço:** CEP, Endereço, Número, Complemento, Bairro, Cidade, UF.

- Lista de clientes com contador ("0 clientes"), estado vazio "Nenhum registro encontrado".
- **Busca por cliente** existe no contrato ("Buscar cliente").
- **Não localizado durante a exploração:** importação em massa, exportação, anexos/documentos,
  histórico financeiro consolidado na ficha, ações em massa, tags/segmentação.
- **Hipótese:** o CEP provavelmente dispara autopreenchimento (padrão de mercado) — *não validado*.

---

## 5. Empréstimos e Contratos

**Rota:** `/web/contract`. Modal "Novo contrato" com duas abas: **Fixo** e **Parcelado**.

### 5.1 Contrato Fixo (evidência `43_fixo_1000_taxa10.png`)
Campos: **Valor / Custo**, **Taxa (%)**, **Pagamento mínimo**, **Primeiro pagamento**, Observação.
Rótulo de total: **"Total Contrato = Custo + Taxa"**.

- Comportamento: é uma **dívida rotativa / "só juros"**. O principal (custo) permanece; a Taxa% gera
  o encargo do período; o **Pagamento mínimo** é o valor mínimo que o devedor paga (tipicamente os
  juros), e o saldo "rola". Uso clássico do mercado informal.

### 5.2 Contrato Parcelado (evidência `42_parc_1000_1300_3x.png`, `31_contract_parcelado.txt`)
Campos: **Valor / Custo**, **Valor a receber** (com **% de markup exibido**), **Frequência**
(Diário/Semanal/Quinzenal/Mensal), **Número de parcelas**, **Primeiro pagamento**,
**Forma de pagamento** (Dias semana Seg-Sex / Dias úteis Seg-Sáb / Todos os dias Seg-Dom),
**Valor das parcelas** (calculado), Observação, **Total Contrato = Valor a receber**.

- Comportamento: o operador informa o **total a receber** (ou o markup %); o sistema gera
  **parcelas iguais**. A frequência + regra de dias definem as **datas de vencimento**.

**Não localizado:** garantias/colateral, multa/mora configuráveis no cadastro do contrato,
renegociação/refinanciamento explícitos, anexos, geração de contrato/CCB em PDF.

---

## 6. Motor Financeiro

Testes independentes (valores digitados, campos calculados lidos ao vivo, **sem salvar**):

### Cenário A — Parcelado
Entrada: Custo **R$ 1.000,00**, Valor a receber **R$ 1.300,00**, **3** parcelas, Mensal.
Resultado do SysJuros:
- **% exibido = 30,0%** → validação: (1300−1000)/1000 = **30%** ✔
- **Valor das parcelas = R$ 433,33** → validação: 1300/3 = **433,33** ✔
- **Total Contrato = R$ 1.300,00** (= Valor a receber) ✔

**Fórmula aparente (fato observado):**
`Parcela = Total_a_receber / n` e `Total = Custo × (1 + markup)`.
→ **Juros FLAT / ADD-ON** (não há recomposição sobre saldo devedor). **Não é PRICE nem SAC.**

### Cenário B — Fixo
Entrada: Custo **R$ 1.000,00**, Taxa **10%**.
Resultado do SysJuros:
- Campo Taxa converteu para **R$ 100,00** (10% de 1.000).
- **Total Contrato = R$ 1.100,00** → validação: 1000 + (1000×10%) = **1.100** ✔

**Fórmula aparente:** `Total = Custo × (1 + i)`, com **Pagamento mínimo** como encargo periódico
(modelo rotativo). *Observação: com Taxa vazia, o Total = Custo (R$1.000), confirmando que a taxa é
somada apenas quando informada.*

**Inferência técnica:** o motor prioriza **simplicidade operacional** sobre rigor financeiro-legal.
Não há evidência de capitalização composta, IOF, CET, juros proporcionais por dias corridos, nem
amortização. Isso é adequado ao público informal, mas **não atende exigências formais** (Bacen/CDC).

---

## 7. Juros e Multas

- **Juros do contrato:** via markup (Parcelado) ou Taxa% periódica (Fixo). **Confirmado.**
- **Multa/mora por atraso:** **Não localizado** como campo de configuração no contrato. Hipótese:
  pode existir em regra global ou não existir. *Não foi possível validar.*
- **Juros compostos / capitalização:** **Não localizado.** Comportamento observado é flat.
- **Desconto/antecipação:** **Não localizado** na criação; possivelmente no fluxo de baixa de
  parcela (módulo Vencimentos) — *não validado por ausência de dados na conta*.

---

## 8. Parcelamentos e Amortização

- **Parcelas fixas (iguais):** **Confirmado** (Total/n).
- **PRICE, SAC, parcelas variáveis, amortização antecipada, refinanciamento:** **Não localizados.**
- Frequências: **Diário, Semanal, Quinzenal, Mensal** (confirmado no dropdown).
- Regras de dias para parcelas diárias: **Seg-Sex, Seg-Sáb, Seg-Dom** (confirmado).

---

## 9. Pagamentos

- Módulo **Vencimentos** (`/web/salaries`) concentra as parcelas: cards **Vencem hoje / Atrasadas /
  A receber / Recebidas**, abas **Todos / Pagos / Não Pagos**, filtro por **período de vencimento**,
  e totais (**Total em Aberto, Mínimo Total, Total Pago**). Evidência: `10_Vencimentos.txt`.
- **Baixa de parcela / pagamento parcial / ordem de aplicação (multa→mora→juros→principal):**
  **Não foi possível validar** — a conta de teste estava sem contratos/parcelas, e não geramos
  parcelas persistentes para preservar o ambiente. **Hipótese** (a confirmar): baixa individual por
  parcela a partir do painel de Vencimentos.

---

## 10. Cobranças

- **Régua de cobrança / lembretes automáticos / templates:** **Não localizados** na conta.
- Existe aba **Notificação** em Configurações (evidência `10_Configuracoes.txt`), mas o conteúdo/
  gatilhos não foram explorados a fundo. **Hipótese:** notificações de vencimento — *não validado*.

---

## 11. WhatsApp / Notificações

- **Não localizada** integração ativa de envio via WhatsApp/SMS/e-mail dentro da conta.
- A landing não promete WhatsApp explicitamente (foco em "contas a receber" e alertas de atraso).
- **Oportunidade forte** para o nosso produto (ver seções 22–24).

---

## 12. PIX / Integrações

- **Não localizado** PIX, QR Code, "copia e cola", link de pagamento ou webhook bancário na conta.
- Integrações técnicas **observadas na camada de rede** (tracking/infra, não de pagamento):
  Google Analytics (`analytics.google.com/g/collect`, `_ga`, `_ga_*`), **Facebook Pixel** (`_fbp`),
  **Utmify** (`tracking.utmify.com.br` — rastreio de UTM/leads), **Algolia** (busca client-side),
  **ipify** (captura de IP). Evidência: `endpoints.txt`, `session.txt`.

---

## 13. Relatórios

**Rota:** `/web/reports` (evidência `10_Relatorios.txt`). Disponíveis:
1. **Evolução gráficos** — clientes, contratos, valor contratado e recebimentos dos últimos 12 meses.
2. **Rentabilidade contratos** — custo, valor recebido, saldo em aberto, **capital exposto** e
   **margem de lucro por contrato**.
3. **Projetado × Realizado** — *"Em breve"* (não implementado).
4. **Custo × Recebido** — *"Em breve"* (não implementado).

- **Exportação CSV/Excel/PDF/impressão: não localizada.** Oportunidade clara.

---

## 14. Dashboard

**Rota:** `/web/dashboard` (evidência `01_after_login.txt`). Componentes:

- **Total em aberto**, **Recebido hoje**, **Ontem**.
- **Resumo do mês** (ex.: Setembro/2026): **Custos** (custo dos contratos), **Recebido/Entradas**,
  **A receber/Em aberto**, **Rentabilidade** (Recebido − Custo), **Novos contratos** (abertos no
  mês), **Novos clientes** (cadastrados no mês).
- **Observação de UX:** mistura de símbolos monetários (`$ 0,00` e `R$ 0,00`) — inconsistência.
- Sem metas, sem projeção de caixa futura, sem alertas acionáveis diretos no dashboard.

---

## 15. UX/UI

**Pontos fortes:** layout limpo, menu lateral fixo claro, foco mobile, formulários em modal com
cálculo ao vivo (Total/parcelas atualizam ao digitar), estados vazios explícitos
("Nenhum registro encontrado"), poucos cliques para as ações principais.

**Fraquezas observadas:**
- Inconsistência de moeda (`$` vs `R$`) no dashboard e nos formulários.
- Navegação Bubble sem URLs semânticas de estado (dificulta deep-link e "voltar").
- `viewport` com `user-scalable=no` (ruim para acessibilidade/zoom).
- Sem exportações, sem ações em massa, sem breadcrumbs.
- Tempo de carregamento inicial alto (bundle Bubble/skeleton).

---

## 16. Arquitetura Técnica Observável

- **Plataforma:** **Bubble.io** (no-code). Evidências: CDN `*.cdn.bubble.io`, `bubble_session_uid`,
  `appquery{app_version:"live"}`, `robots.txt` com `Disallow: /version-test/`.
- **Renderização:** **CSR** (client-side); HTML inicial é "skeleton" + JS pesado.
- **APIs internas do Bubble** (tráfego da própria conta, evidência `endpoints.txt`):
  - `POST /elasticsearch/msearch|search|mget|maggregate` → busca/consulta de dados.
  - `POST /workflow/start` → execução de workflows (ações de negócio).
  - `POST /user/hi|m|apm`, `POST /bug/client_log` → telemetria/sessão Bubble.
  - `GET /api/1.1/init/data` → bootstrap de dados.
- **Sessão:** cookies `sysjuros_live_u2main` (+ `.sig`) e `sysjuros_u1main`; `localStorage`
  com `algoliasearch-client-js`, `lead`, referrers. (Somente **nomes** de chaves registrados.)
- **Terceiros:** GA4, Facebook Pixel, Utmify, Algolia, ipify.
- **Implicação:** difícil de escalar/personalizar, custo por WU (workload units) do Bubble, SEO
  limitado. Nosso stack (React + FastAPI + Mongo) é vantagem estrutural.

---

## 17. SEO Técnico

Auditoria em `https://sysjuros.com.br` (evidência: crawls + `curl`):

- **robots.txt:** apenas `User-agent: *` / `Disallow: /version-test/`. **Sem referência a sitemap.**
- **sitemap.xml:** **inexistente** (retorna página 404 do Bubble). ❌
- **Renderização:** CSR (Bubble) — conteúdo depende de JS; ruim para indexação. ❌
- **canonical:** **ausente** no `<head>`. ❌
- **meta description:** **ausente** (og:description vazio). ❌
- **Schema.org / JSON-LD:** **nenhum** (sem `application/ld+json`). ❌
- **viewport:** `user-scalable=no` (penaliza acessibilidade). ⚠️
- `lang="pt"`, `theme-color #1a7a4a`, `<meta name="fragment" content="!">` (esquema AJAX-crawling
  **obsoleto** desde 2015). ⚠️
- **Uma única URL indexável** relevante (a landing). Sem blog, sem páginas de conteúdo.

**Conclusão:** SEO praticamente inexistente. **Oportunidade enorme** — nosso GestorCred já possui
**prerender SSR** e múltiplas landing pages temáticas + componente `JsonLd` (ver seção 22).

---

## 18. SEO On-Page

- **`<title>`:** "SysJuros - Controle de Cobranças".
- **OG/Twitter title:** "Financeiro - Contas a receber"; `og:site_name` = SysJuros;
  `twitter:card` = summary_large_image; `og:image` = logo; `og:type` = website.
- **H1/H2 (conteúdo da landing):** "Por que Escolher Nossa Solução?", "Funcionalidades Essenciais",
  "Solução barata que resolve o controle da sua gestão", "Tem alguma dúvida?", "Venha se juntar a nós".
- **Densidade/semântica:** cobre "empréstimos", "cobranças", "contas a receber", "parcelas",
  "recebíveis", "margem de lucro". Rodapé com termo-chave: *"Sistema de Empréstimos e Cobranças"*.
- **Fraquezas:** headings pouco otimizados para intenção de busca; sem FAQ marcado com schema;
  sem conteúdo informacional/blog; imagens sem `alt` significativo (CDN Bubble).

---

## 19. Palavras-Chave e Conteúdo

- **Intenção comercial coberta:** "sistema de empréstimos", "controle de cobranças",
  "contas a receber", "gestão de parcelas".
- **Lacunas de conteúdo (oportunidade nossa):** "calculadora de juros", "sistema para credores",
  "cobrança por WhatsApp", "cobrança PIX", "consulta CPF crédito", "contratos digitais/CCB",
  "sistema microcrédito", "gestão de carteira de crédito". *(Note: o nosso projeto já tem rotas
  planejadas para vários desses termos — ver `frontend/scripts/prerender.js`.)*
- FAQ presente (perguntas sobre pagamento, limitações, acesso multiplataforma, garantia), mas
  **sem `FAQPage` schema**.

---

## 20. Pontos Fortes Observados

1. **Simplicidade extrema** — curva de aprendizado baixa, foco no operador informal.
2. **Preço agressivo** (R$ 37/mês, plano único).
3. **Cálculo ao vivo** nos formulários (feedback imediato de parcela/total).
4. **Modelo Fixo (rotativo) + Parcelado** cobre os 2 casos mais comuns do nicho.
5. **Flexibilidade de frequência** (diário/semanal/quinzenal/mensal + regra de dias úteis).
6. **Painel de Vencimentos** bem pensado (hoje/atrasadas/a receber/recebidas + totais).
7. **Mobile-first** e "dados na nuvem".

---

## 21. Problemas / Limitações Observados

1. **Motor financeiro simplista** (flat/add-on) — sem PRICE/SAC, sem CET/IOF, sem juros compostos.
2. **Sem cobrança automatizada** (WhatsApp/SMS/e-mail) localizada na conta.
3. **Sem PIX / link de pagamento / baixa automática.**
4. **Sem consulta de CPF / score** no cadastro.
5. **Sem exportação** (CSV/Excel/PDF) nos relatórios.
6. **Sem geração de contrato/CCB em PDF.**
7. **2 relatórios "Em breve"** (Projetado×Realizado, Custo×Recebido) — funcionalidade prometida e
   não entregue.
8. **SEO inexistente** (sem sitemap/description/canonical/schema; CSR).
9. **Inconsistências de UX** (símbolo de moeda `$`/`R$`).
10. **Multa/mora não configurável** no contrato (não localizada).
11. **Dependência do Bubble** (custo por WU, teto de performance/customização).

---

## 22. Oportunidades para Nosso Sistema

> Contexto do nosso GestorCred (observado no repositório/infra): React + FastAPI + Mongo, com
> integrações já provisionadas — **LosDados (consulta CPF)**, **Stripe**, **Turnstile**, **SMTP**,
> **EMERGENT_LLM_KEY (IA)** — e SEO real (prerender SSR + rotas temáticas + `JsonLd`).

1. **Motor financeiro correto e configurável** (PRICE, SAC, juros simples/compostos, mora+multa,
   IOF, **CET**) — diferencial de conformidade que o SysJuros não tem.
2. **Cobrança automatizada por WhatsApp** (régua: pré-vencimento, vencimento, atraso D+1/D+3/D+7),
   com templates e variáveis. *(Requer provedor de WhatsApp — a definir com o usuário.)*
3. **PIX com QR/copia-e-cola + baixa automática** via webhook (usar Stripe/PSP já provisionado).
4. **Consulta de CPF/score no cadastro** (LosDados já provisionado) → antifraude e análise.
5. **Contrato digital / CCB em PDF** com assinatura.
6. **Relatórios exportáveis** (CSV/Excel/PDF) + **fluxo de caixa projetado** e DRE — entregar o que
   eles marcam como "Em breve".
7. **SEO dominante**: sitemap, schema (`SoftwareApplication`, `FAQPage`, `Organization`),
   landing pages por intenção (calculadora de juros, cobrança WhatsApp/PIX, microcrédito).
8. **IA (EMERGENT_LLM_KEY)**: resumo de risco do cliente, sugestão de mensagem de cobrança,
   assistente de renegociação.

---

## 23. Roadmap P0 / P1 / P2

**P0 — impacto alto / imediato**
- Motor financeiro com PRICE/SAC + mora/multa + CET (paridade + superação).
- Cobrança WhatsApp com régua automática (maior dor operacional do nicho).
- PIX + baixa automática.

**P1 — impacto relevante**
- Consulta CPF/score no cadastro (LosDados).
- Relatórios exportáveis + fluxo de caixa projetado.
- Contrato/CCB em PDF.

**P2 — oportunidade futura**
- IA para cobrança/renegociação e score de inadimplência.
- App mobile/PWA dedicado.
- Marketplace de templates de mensagem; multiusuário/permissões.

---

## 24. Matriz Comparativa

| Recurso | SysJuros | Nosso Sistema (GestorCred) | Oportunidade | Prioridade |
|---|---|---|---|---|
| Contrato Fixo (rotativo) | ✅ | A confirmar | Paridade | P1 |
| Contrato Parcelado (flat) | ✅ | ✅ (simulação) | Paridade | P0 |
| PRICE / SAC / CET / IOF | ❌ | Provável (simulação) | **Superação** | P0 |
| Multa / Mora configurável | ❌ (não localizado) | A confirmar | **Superação** | P0 |
| Frequência D/S/Q/M | ✅ | A confirmar | Paridade | P1 |
| Painel de Vencimentos | ✅ | ✅ (relatórios) | Paridade+ | P1 |
| Cobrança WhatsApp | ❌ | A implementar | **Superação** | P0 |
| PIX / link pagamento / baixa auto | ❌ | Stripe provisionado | **Superação** | P0 |
| Consulta CPF / score | ❌ | LosDados provisionado | **Superação** | P1 |
| Contrato/CCB PDF | ❌ | A implementar | **Superação** | P1 |
| Exportação CSV/PDF | ❌ | A implementar | **Superação** | P1 |
| Relatórios avançados/fluxo caixa | Parcial (2 "Em breve") | A implementar | **Superação** | P1 |
| IA (resumo/cobrança) | ❌ | EMERGENT_LLM_KEY | **Superação** | P2 |
| SEO (sitemap/schema/SSR) | ❌ | ✅ prerender + JsonLd | **Superação** | P0 |
| Preço | R$ 37/mês | A definir | Posicionamento | — |
| Stack | Bubble (no-code) | React+FastAPI+Mongo | Estrutural | — |

Legenda: ✅ existe / ❌ ausente / "A confirmar" = não auditado no nosso código nesta sessão.

---

## 25. Cenários Financeiros Testados

| # | Tipo | Entrada | Saída SysJuros | Validação independente | Fórmula aparente |
|---|---|---|---|---|---|
| A | Parcelado | Custo 1.000; Receber 1.300; 3x; Mensal | %=30,0%; Parcela=R$433,33; Total=R$1.300 | 30%=(1300-1000)/1000; 433,33=1300/3 ✔ | Flat: Parcela=Total/n; Total=Custo×(1+markup) |
| B | Fixo | Custo 1.000; Taxa 10% | Taxa=R$100,00; Total=R$1.100 | 100=1000×10%; 1.100=1000+100 ✔ | Total=Custo×(1+i); mín. = juro periódico |
| B0 | Fixo | Custo 1.000; Taxa vazia | Total=R$1.000 | 1.000=Custo ✔ | Taxa só soma quando informada |

*Observação: cenários de pagamento parcial/antecipado/atraso e ordem de aplicação **não foram
validados** por ausência de parcelas persistidas (ambiente preservado, sem salvar contratos).*

---

## 26. Evidências

Arquivos em `/app/bench/out/` (uso interno; não contêm credenciais):

- `00_login.png` — tela de login.
- `01_after_login.txt/.png` — dashboard pós-login (KPIs).
- `10_Clientes / 10_Contratos / 10_Vencimentos / 10_Relatorios / 10_Configuracoes` — módulos.
- `20_contract_form` — formulário Contrato **Fixo**.
- `31_contract_parcelado` — formulário Contrato **Parcelado** (campos).
- `42_parc_1000_1300_3x` — cenário A (Parcelado) calculado ao vivo.
- `43_fixo_1000_taxa10` — cenário B (Fixo) calculado ao vivo.
- `21_customer_form` — formulário de cliente.
- `endpoints.txt` / `network.json` — endpoints Bubble observados.
- `session.txt` — nomes de cookies/localStorage (sem valores).

---

## 27. Conclusão Técnica

O SysJuros é um produto **enxuto, barato e eficaz para o público informal**, cuja força está na
**simplicidade** e no **preço** — não na profundidade financeira nem na tecnologia. Seu motor é
**flat/add-on** (verificado), a stack é **Bubble/CSR** (com limites de performance e SEO), e faltam
recursos hoje decisivos no nicho: **cobrança automatizada (WhatsApp/PIX)**, **consulta de CPF**,
**contratos digitais**, **exportações** e **relatórios preditivos**.

Nosso GestorCred pode **empatar na simplicidade** e **vencer no que importa**: motor financeiro
correto (PRICE/SAC/CET), automação de cobrança, PIX com baixa automática, consulta CPF e **SEO real**
— áreas onde já temos base técnica e integrações provisionadas.

### Cobertura da exploração
- **Módulos encontrados (autenticados): 6** (Dashboard, Clientes, Contratos, Vencimentos, Relatórios, Configurações) + Como usar/Suporte.
- **Explorados [✓]: 5** (Dashboard, Clientes, Contratos, Vencimentos, Relatórios).
- **Parcialmente [~]: 1** (Configurações — abas Plano/Notificação não aprofundadas).
- **Não explorados [ ]: fluxos de pagamento/baixa** (ambiente sem dados; não persistimos contratos
  para preservar a conta) e **Como usar/Suporte** (conteúdo de ajuda, baixa prioridade).
- **Motivo:** conta de teste vazia (0 clientes/0 contratos) + decisão de **não salvar** registros
  para não poluir o ambiente. O motor financeiro foi validado via **cálculo ao vivo**, sem persistir.

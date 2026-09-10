# GestorCred / Kredor — PRD & Setup Notes

## Original request (2026-06)
User imported an existing project (already present in `/app`), asked to run `iniciar.sh`,
bring the stack online, import the attached MongoDB backup, and apply the provided
backend/frontend `.env` values.

## What it is
**Kredor / GestorCred** — SaaS for managing personal/informal loans with automatic
PIX + WhatsApp collection, CPF credit analysis, client portal, subscriptions, and wallet.

## Tech stack
- Backend: FastAPI (`/app/backend`, entry `server.py` -> `main.py`), APScheduler jobs.
- Frontend: React + CRACO + Tailwind (`/app/frontend`).
- DB: MongoDB (local standalone; app handles absence of transactions gracefully via
  `utils/transacao.py`).
- Integrations: LosDados (CPF), Stripe/MercadoPago, SMTP, Cloudflare Turnstile, WhatsApp.

## Setup done (2026-06)
- Restored MongoDB dump into DB `gestorcred` (8818 docs: 7 usuarios, 47 clientes, 90 emprestimos).
- Wrote `/app/backend/.env` with user-provided values. Empty `APP_URL` set to the preview
  URL and added `CORS_ORIGINS` (preview + localhost) so the frontend origin passes CORS
  (dev mode allows localhost + APP_URL).
- Wrote `/app/frontend/.env` with `REACT_APP_BACKEND_URL` = preview URL, `WDS_SOCKET_PORT=443`,
  `REACT_APP_TURNSTILE_SITE_KEY`.
- `pip install -r requirements.txt`; frontend `node_modules` already present.
- Restarted `backend` + `frontend` via supervisor. Backend health `GET /api/` -> 200.
  Landing page renders; scheduler running.

## Status
Application is LIVE and functional end-to-end (landing page loads, backend healthy,
DB restored, auth route reachable/Turnstile-protected).

## Fase 1.5 — Correções (concluída em 2026-06, verificada por pytest)
Ambiente: container Emergent (`/app`, supervisor, MongoDB standalone) — não a VPS do doc.
- **1.5.1** Valores negativos em empréstimos pequenos: `services/calculos.py`
  - `_plano_parcelas_fixas` agora divide principal e juros separadamente (soma = total),
    nunca gera principal/juros negativos.
  - `calcular_tabela_price` limita amortização ao saldo (`min(pmt-juros, saldo)`).
  - Validação `principal < periodos` → `DivisaoInvalidaError` (mapeada p/ HTTP 422 em `main.py`).
  - Prova: `tests/test_dinheiro.py` — **2865 passed** (grade Price/SAC/fixas + 422).
- **1.5.2** `utils/transacao.py`: em produção sem replica set levanta RuntimeError; em dev
  loga warning uma vez. Prova: RuntimeError confirmado com ENVIRONMENT=production.
- **1.5.3** `pytest-asyncio==1.4.0` + `backend/pytest.ini` (asyncio_mode=auto). Os 3 testes de
  race condition agora RODAM e passam (antes: skipped/warning).
- **1.5.4** `scripts/checar_session_em_transacao.py` estendido: além de `db.*`, cobre chamadas
  `await` de service dentro do bloco transacional (allowlist explícita). exit 0 no código real.
- **1.5.5** `frontend/Dockerfile` → `node:20-alpine` (yarn.lock fixa react-router-dom@7 >=node20).
  Nota: `docker compose build` não roda neste preview (sem daemon); mudança aplicada por inspeção.

Falhas de teste restantes NÃO são regressão: testes de login/Turnstile/segurança (precisam de
HTTP + credencial real) e jobs de empréstimos abertos (dado restaurado tem campo int None num
`Parcela` — confirmado idêntico ANTES das minhas mudanças via git stash).

## Fase 2 + unblockers (concluído nesta sessão 2026-06)
- **Dado Restaurado**: backup era pré-migração de centavos (campos float sem `_centavos`).
  Rodado `scripts/migrar_para_centavos.py` → 90 empréstimos, 340 parcelas, 210 pagamentos migrados.
  Fix defensivo em `parcela_service.py` (`saldo_devedor_centavos ... or 0`). Job de empréstimos
  abertos volta a rodar sem crash (36 abertos processados, 0 erro).
- **Acesso E2E**: `scripts/seed_usuario_e2e.py` cria `e2e@gestorcred.com.br` / `E2eTest@2026`.
  Validado E2E via API: login OK; `/api/emprestimos/simular` R$10.000/12x/2% Price = PMT R$945,60,
  soma principal exata, 0 negativos; principal ínfimo → HTTP 422.
- **Fase 2.1 (logging + request_id)**: CONCLUÍDA. 289 `print()` → `logger.<nível>` em
  routes/services/jobs (0 prints restantes; `assinaturas.py.backup` morto removido). `request_id`
  por requisição via contextvar + middleware em `main.py`, injetado em ambos os formatters e echoado
  no header `X-Request-ID`. Verificado: logs carregam `[req:...]`. 3169 testes coletam sem erro de import.
- **Fase 2.3 (N+1) — parcial**: `routes/dashboard.py` — 3 N+1 (linhas ~180/288/362) trocados por
  lookup em lote (`$in`) com filtro `usuario_id`. Verificado E2E (dashboard 200, nomes de cliente
  resolvidos, total correto). Script `checar_query_em_laco.py` do doc NÃO existe neste repo.

## Backlog / Next
- Bug corrigido (2026-06): **dashboard 500**. Duas causas: (1) dados legados com campos
  `*_centavos` em float → `scripts/corrigir_centavos_float.py` (10 campos) + coerção `int()` em
  `dashboard.py` (`_valor_devido_parcela`, `total_capital`); (2) `frontend/public/env-config.js`
  apontava para `cred-portal-test.preview...` (backend errado) → corrigido para a URL do preview.
  Verificado E2E pela UI (login Diego + dashboard renderiza com dados reais, todas as APIs 200).
- P1: **Fase 2.2** (datas como Date do BSON) — migração coordenada (ler-ambos → migrar → só-Date),
  risco alto; ~352 `.isoformat()` + `utcnow()`. NÃO iniciada.
- P1: **Fase 2.3 restante** (~45 N+1 em 16 arquivos): `emprestimos.py` (insert_one em laço →
  insert_many/bulk_write), `analise.py`, `whatsapp.py`, `parcelas.py`, etc. Somente dashboard feito.
- P2: **Fase 3** (gateway único, arquivos mortos, imports em função, cálculo só no backend, frontend).
- Nota: `services/notificacao_service_v2.py` ainda vivo (import em função) — resolver junto com 3.2.

---

## Sessão 10/06/2026 — Setup + Correções técnicas (Fase 2 crítica + 3.2)

### Ambiente
- App online: backend (FastAPI :8001), frontend (React :3000), MongoDB standalone (DB `gestorcred`).
- `.env` de backend/frontend criados conforme fornecido; domínio de preview canônico: `cred-manager-dev.preview.emergentagent.com`.
- Seed executado (`python -m seeds.seeder`): usuários de teste em `/app/memory/test_credentials.md`.
- Banco anexado NÃO recebido nesta execução — usados dados de seed.

### Correções concluídas e verificadas
- **2.4** `exc_info=True` normalizado em `logging_service._log` (→ `sys.exc_info()`); traceback volta ao log JSON, sem `--- Logging error ---`.
- **2.5** Testes de race condition isolados via `loop_scope="module"` (causa real neste ambiente: cliente motor global preso a event loop fechado). 3 passed em 2 execuções.
- **2.6** Migração `migrar_para_centavos.py` não grava mais valor não-convertível (loga e pula); `corrigir_centavos_float.py` usa união real de campos e cobre todos os tipos != int/long; `int(round())` removido de `dashboard.py`; verificação de integridade de centavos no boot (`_verificar_integridade_centavos`).
- **3.2** Arquivos mortos removidos (`Checkout.js.bak`, `notificacao_service_v2.py`); `notificacao_service_v2` incorporado a `notificacao_service.py` (import de função eliminado).
- Testes: `test_dinheiro` 2865 passed; `test_correcoes_fase2` 5 passed; testing_agent backend 7/7 (100%).

### Backlog restante do plano (itens grandes, exigem iterações dedicadas)
- **2.2** Datas como `Date` do BSON (318 `.isoformat()`, 31 `utcnow()`) — requer migração coordenada de dados + código.
- **2.3** N+1 (45 queries em 17 arquivos; dashboard já em grande parte em lote) — resolver por arquivo (emprestimos.py, analise.py primeiro).
- **3.1** Gateway único de pagamento — DECISÃO DE NEGÓCIO pendente (qual gateway é o oficial).
- **3.3** Quebrar ciclos de import (183 imports em função → <20).
- **3.4** Cálculo financeiro só no backend — `JurosCalculator.js` é público; `/api/emprestimos/simular` exige auth. Precisa de endpoint público de simulação.
- **3.5** Refatorar componentes gigantes (>2400 linhas), 27 axios diretos, 3 `process.env`, 91 catches só com console.error.

### 3.1 Gateway único — CONCLUÍDO (10/06/2026)
Decisão do usuário: manter **Asaas + SyncPay**; remover **Mercado Pago + PagSeguro**.
- Removidos `services/mercadopago.py`, `services/mercadopago_assinatura.py`, `services/pagseguro.py` (não importados).
- `models/configuracao.py`: modelo legado `GatewayConfig` (com MP/PagSeguro) removido.
- `routes/assinaturas.py`: endpoints MP neutralizados (410) e ramo MP de `/gateway/disponiveis` removido.
- `seeds/seeder.py` e `plano_service.py`: default agora Asaas (`asaas_only`).
- Verificado: `/api/assinaturas/gateway/disponiveis` retorna `asaas`; backend sobe sem erros; `ls services | grep -icE "asaas|mercadopago|pagseguro|syncpay"` = 2.
- Pendência menor (não bloqueante): página frontend órfã `CheckoutTransparenteBrick` (MP) — pode ser removida depois; não é alcançada no fluxo normal.

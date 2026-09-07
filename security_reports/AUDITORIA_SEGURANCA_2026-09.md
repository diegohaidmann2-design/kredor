# Auditoria de Segurança — GestorCred (2026-09-07)

Escopo: portas de entrada (login, cadastro, recuperação, APIs públicas/autenticadas/admin,
consultas, carteira, sessões/tokens, bots/brute-force, injeção, IDOR, mass assignment, webhooks).
Método: ANALISAR → MAPEAR → TESTAR → CORRIGIR → RETESTAR (backend, curl + mongosh + pytest).

> Isto é uma avaliação técnica baseada nos testes realizados. NÃO significa que a
> aplicação está "100% segura".

## Superfície de ataque (rotas realmente públicas, sem auth)
- `POST /api/auth/{registro,login,refresh,verify-2fa,resend-2fa,reenviar-verificacao}`, `GET/POST /api/auth/verificar-email/{token}`
- `GET /api/assinaturas/{planos,social-proof,gateway/disponiveis,cupom/validar,payment-status,syncpay-status}`
- `POST /api/assinaturas/{checkout-syncpay,checkout-asaas,webhook-syncpay,webhook-asaas}` (webhook-mercadopago = 410)
- `GET /api/configuracoes/landing`, `GET /api/contratos/templates`
- `POST /api/portal/{login,solicitar-codigo}`, `POST /api/equipe/aceitar-convite`
- `GET /api/cadastro-publico/info/{token}`, `POST /api/cadastro-publico/solicitar/{token}`
- `GET /api/upload/files/{path}` (paths com UUID, não enumeráveis)

## Vulnerabilidades encontradas e corrigidas

### 🔴 CRÍTICO — Bypass de pagamento via webhook SyncPay (payment forgery)
- **Endpoint:** `POST /api/assinaturas/webhook-syncpay` (`routes/assinaturas.py`)
- **Problema:** endpoint público (rate-limit ignora `/webhook`). A validação HMAC só
  ocorria *se* `syncpay_webhook_secret` estivesse configurado — e ele está **vazio** no
  banco. Resultado: o corpo do webhook era confiável e um atacante podia enviar
  `status:"completed"` + `external_reference:<user_id>` e **ativar qualquer plano pago
  de graça** (ou creditar carteira).
- **Evidência (antes/depois):** POST forjado com `transaction_id:"FORGED-999"` →
  o backend agora reconsulta o gateway (`consultar_transacao`), recebe **404**, e
  **não** cria transação/movimento nem ativa plano (contagens no Mongo inalteradas).
- **Correção:** o webhook nunca confia no corpo; **reconfirma sempre** status e valor
  direto na API SyncPay antes de liberar plano/crédito. Só `status == "completed"`
  confirmado pelo gateway libera. Sem `transaction_id` ou gateway indisponível → ignora.
- **Retest:** ✅ forjado não muta estado (pytest + mongosh).

### 🟠 ALTO — Endpoints administrativos de cupom sem autenticação
- **Endpoints:** `POST /api/admin/transacoes/cupom/usar/{codigo}`,
  `GET /api/admin/transacoes/cupom/validar/{codigo}` (`routes/admin_transacoes.py`)
- **Problema:** faltava `Depends(require_admin)` (os demais endpoints do arquivo tinham).
  `cupom/usar` permitia a **qualquer um marcar/queimar cupons** por código.
- **Correção:** adicionado `dependencies=[Depends(require_admin)]` a ambos. O checkout
  público continua usando o endpoint próprio `/api/assinaturas/cupom/validar/{codigo}`.
- **Retest:** ✅ 401 sem token; 403 para usuário comum; 200 para admin.

### 🟡 MÉDIO — Brute force / credential stuffing só por e-mail (sem dimensão de IP)
- **Endpoint:** `POST /api/auth/login`
- **Problema:** o bloqueio era **apenas por e-mail** (5 falhas/15min → 30min). Isso
  (a) não continha credential-stuffing distribuído por conta a partir de um mesmo IP e
  (b) o rate-limit em memória (50/min) é por-processo (não distribuído).
- **Correção:** adicionada proteção **por IP** combinada à existente por conta
  (`services/brute_force_service.py`, coleção `login_attempts_ip`, extração correta de
  IP via `X-Forwarded-For`): 20 falhas de login (qualquer conta) por IP na janela →
  bloqueio de 30min. Mantido o bloqueio por conta para brute force direcionado.
- **Retest:** ✅ 429 após ~20 falhas em contas diferentes do mesmo IP; bloqueio por
  conta ainda funciona; login legítimo intacto.

### 🔵 BAIXO — Hardening de CORS (dev)
- `security.get_cors_origins()` tinha host de preview antigo fixo. Passou a derivar de
  `APP_URL` do ambiente. Em produção continua exigindo `CORS_ORIGINS` explícito.

## Itens verificados e considerados OK (sem alteração)
- **Injeção SQL:** não há SQL/ORM — banco é MongoDB via motor com queries parametrizadas
  (dicts). Sem `$where`/`eval`/f-string em query. `$regex` só em campos de busca já
  autenticados/admin. Login com `{"$ne":null}` é barrado pelo schema Pydantic (422).
- **Senhas:** `passlib` **bcrypt** (`$2b$`); mínimo 6 chars no registro; sem log de senha.
- **Sessões/tokens:** JWT HS256 access(8h)+refresh(30d) com `type`, `jti` e blacklist
  (`tokens_revogados`); `get_current_user` revalida usuário/ativo no banco.
- **IDOR / isolamento:** consultas, carteira, clientes, empréstimos e parcelas filtram
  por `usuario_id`/`owner_id`. `GET /consultas/{id}` de outro dono → 404.
- **Mass assignment:** updates admin usam modelos Pydantic (whitelist); `senha`→hash.
- **Carteira:** débito/crédito atômico via `find_one_and_update` com guarda de saldo;
  recarga idempotente por `payment_id`; preços definidos pelo backend (não pelo cliente);
  `RecargaRequest` valida faixa de valor.
- **Webhook Asaas:** valida header `asaas-access-token` (constant-time) — gateway desativado.
- **XSS:** frontend sem `dangerouslySetInnerHTML`.
- **Headers:** CSP, X-Content-Type-Options, X-Frame-Options=DENY, Referrer-Policy,
  Permissions-Policy, HSTS (produção) via `SecurityMiddleware`.
- **Enumeração:** `reenviar-verificacao` e `resend-2fa` retornam resposta genérica.
- **Path traversal (restore):** `backup_service` já sanitiza `TarInfo` (fix anterior).

## Riscos remanescentes / recomendações de hardening
1. Rate-limit global é **em memória** (por processo). Em produção multi-worker, migrar
   para store compartilhado (a proteção brute-force de login já é MongoDB/compartilhada).
2. Nenhum CAPTCHA/Turnstile no cadastro/login — hoje a defesa é rate-limit por e-mail+IP.
   Para tráfego hostil real, considerar Cloudflare Turnstile validado no backend.
3. Configurar `syncpay_webhook_secret` (HMAC) além da reconfirmação no gateway (defesa em
   profundidade) e o `asaas_webhook_token` quando o Asaas for reativado.
4. `routes/assinaturas.py` tem ~2.4k linhas — refatorar em módulos (não é problema de segurança).

## Como retestar
Suite de regressão: `/app/backend/tests/test_security_audit.py`
(rode os testes de brute-force por último — eles criam bloqueios de IP e limpam ao final).

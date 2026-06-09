# Gestor Cred - Sistema de Gestão de Empréstimos a Juros

## Problema Original
"importei meu projeto, coloque para rodar" — projeto Gestor Cred v2.1.0 importado e colocado em execução. Depois: importação de backup de produção e bug-fix de duplicação de parcelas.

## Arquitetura
- **Backend**: FastAPI 0.110.1 (Python) — `/app/backend`
- **Frontend**: React 19 + CRA/Craco + TailwindCSS + Radix UI — `/app/frontend`
- **Banco**: MongoDB (Motor async) — DB `gestorcred_dev`
- **Scheduler**: APScheduler (jobs cron/interval em background)

## Trabalho Realizado (09/06/2026)

### Sessão 1 — Setup
- `/app/backend/.env` e `/app/frontend/.env` criados com `MONGO_URL`, `DB_NAME`, `REACT_APP_BACKEND_URL`, `JWT_SECRET_KEY`, `FIELD_ENCRYPTION_KEY`, `CORS_ORIGINS=*`.
- Dependências instaladas (`pip install`, `yarn install`).
- Supervisor restart — backend e frontend rodando.

### Sessão 2 — Usuários seed
- Rodado `seeds.usuarios_seeder` (3 usuários: diego admin, admin@gestorcerd, usuario@teste).

### Sessão 3 — Restore de backup de produção
- `mongorestore` do backup `backup-20260609-170303.tar.gz` para o DB `gestorcred_dev` (4.823 documentos, mapeado `gestorcred.* → gestorcred_dev.*`).
- 8 usuários reais restaurados + 35 clientes + 46 empréstimos + 171 parcelas + 81 pagamentos.

### Sessão 4 — Bug fix: Parcelas duplicadas (race condition)
**Causa raiz**: Job `job_gerar_parcelas_emprestimos_abertos` (cron 00:10 UTC diário) executando em paralelo em múltiplas réplicas/workers. 9 grupos de parcelas duplicadas, 7 empréstimos afetados, todos os timestamps de criação separados por microssegundos.

**Correções aplicadas**:
1. `/app/backend/scripts/limpar_parcelas_duplicadas.py` (NOVO) — script idempotente com dry-run que faz soft-delete das duplicatas e re-vincula pagamentos ao keeper. **9 duplicatas resolvidas, 3 pagamentos re-vinculados.**
2. `/app/backend/main.py` — índice único parcial `(emprestimo_id, numero_parcela)` com `partialFilterExpression: {deleted: false}` criado no startup. Normalização do campo `deleted=false` em parcelas legadas.
3. `/app/backend/jobs/emprestimos_abertos_job.py` — try/except em `insert_one` que ignora silenciosamente `DuplicateKeyError` (race evitada).
4. `/app/backend/routes/pagamentos.py` — mesmo padrão de proteção contra DuplicateKey na geração da próxima parcela ao quitar uma parcela.
5. `/app/backend/main.py` — flag `RUN_SCHEDULER` (default `true`) para permitir desabilitar o scheduler em réplicas adicionais em produção.

### Sessão 5 — Testes automatizados
- `/app/backend/tests/test_race_condition_parcelas.py` (NOVO) — 3 testes pytest (também rodáveis como módulo):
  - Teste 1: 20 inserts paralelos com mesmo (emp, número) → 1 sucesso + 19 bloqueados pelo índice
  - Teste 2: 5 execuções concorrentes do job → 0 duplicações
  - Teste 3: 3 jobs + 3 endpoints `/pagamentos` em paralelo → 0 duplicações, 0 erros vazados
  - **Todos passaram ✅**

### Sessão 6 — Bug fix: Empréstimo "quitado" com parcelas pendentes (10/06/2026)
**Causa raiz**: O endpoint `POST /emprestimos/{id}/quitar` (empréstimo aberto) gerava uma parcela EXTRA (numero+1) com capital + mais um período de juros e marcava o empréstimo como `quitado` na hora, SEM dar baixa — deixando a parcela de juros anterior e a nova parcela ambas `pendente`. Resultado: empréstimo quitado exibindo parcelas pendentes (caso SANDOVAL, emp `2d778b30...`).

**Correções aplicadas**:
1. `/app/backend/routes/emprestimos.py` (`quitar_emprestimo_aberto`) — reescrito: ao quitar, a 1ª parcela em aberto (período atual) vira a parcela final = **capital + juros do período**, marcada como PAGA; parcelas futuras em aberto são canceladas (soft-delete); registra um pagamento `tipo=quitacao`; marca o empréstimo `quitado`. Garante 0 parcelas pendentes.
2. `/app/frontend/src/pages/Emprestimos.js` — texto do modal de confirmação/sucesso atualizado para refletir o encerramento imediato.
3. `/app/backend/scripts/corrigir_quitados_inconsistentes.py` (NOVO) — corrige dados legados: empréstimos `quitado` sem pagamentos reais e com parcelas em aberto → revertidos para `ativo` e parcela de quitação indevida cancelada. **1 corrigido (Sandoval).**
4. `/app/backend/tests/test_quitar_emprestimo_aberto.py` (NOVO) — teste e2e contra o servidor: capital+juros cobrados, parcela futura cancelada, sem pendências. **PASSOU ✅.**

### Sessão 7 — Feature: Recibo de Quitação em PDF + envio WhatsApp (10/06/2026)
- `routes/emprestimos.py` — novo endpoint `GET /emprestimos/{id}/recibo-quitacao` que gera PDF "RECIBO DE QUITAÇÃO" (cliente, contrato, capital, juros, total pago, datas, declaração de quitação). Só permitido para empréstimos `quitado` (400 caso contrário). Registra auditoria `GERAR_RECIBO_QUITACAO`.
- `frontend/src/api/api.js` — `reciboQuitacao(id)` (blob).
- `frontend/src/pages/Emprestimos.js` — no menu de empréstimos `quitado`: "Recibo de Quitação (PDF)" (download) e "Enviar Recibo no WhatsApp" (abre wa.me com mensagem pré-preenchida ao telefone do cliente). data-testids: `btn-recibo-quitacao-pdf`, `btn-recibo-quitacao-whatsapp`.
- **Testado**: PDF 200 com valores corretos (Sandoval: capital R$1.200 + juros R$179,76 = R$1.379,76), 400 para empréstimo ativo. ✅

## Status Atual
- Backend ✅ `:8001` (healthy v2.1.0)
- Frontend ✅ `:3000` (landing GestorCred)
- MongoDB ✅ DB `gestorcred_dev` populado com dados reais
- Scheduler ✅ rodando (10+ jobs, com proteção de race condition)
- 0 parcelas duplicadas no banco
- Índice único `uniq_emprestimo_numero_parcela_ativa` ativo

## Backlog
- **P0**: Reset de senha de algum usuário admin (pendente — usuário ainda não confirmou). Hoje login API responde "Credenciais inválidas" porque senhas do backup são as originais de produção.
- **P0**: Deploy em produção:
  1. Subir os 3 arquivos modificados + script + teste
  2. Rodar `python -m scripts.limpar_parcelas_duplicadas --apply` no prod (1 vez)
  3. Definir `RUN_SCHEDULER=true` em apenas 1 pod, demais réplicas `RUN_SCHEDULER=false`
- **P1**: Configurar credenciais Stripe, MercadoPago, SyncPay PIX, SMTP, EMERGENT_LLM_KEY conforme necessário
- **P2**: Adicionar lock distribuído via collection `job_locks` (defesa em profundidade complementar ao índice único)
- **P2**: Refatorar arquivos `.py` com terminadores CRLF para LF (afeta search_replace tool)

## Credenciais
- Ver `/app/memory/test_credentials.md` (atualizado). Senhas dos seeders (`muda2025`, `admin123`, `senha123`) **NÃO funcionam** após restore do backup — usar senhas originais de produção ou solicitar reset.

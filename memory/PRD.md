# GestorCred / Kredor — PRD & Log de Execução

## Problema / Contexto
Sistema de gestão de empréstimos e cobrança (PIX/WhatsApp). Stack: FastAPI + React + MongoDB.
Projeto importado e colocado no ar; banco `gestorcred` restaurado a partir de dump (mongorestore).
Trabalho guiado pelo `PLANO_CORRECOES.md` (fases 1→3).

## Ambiente
- backend/.env e frontend/.env preenchidos; `REACT_APP_BACKEND_URL` e `APP_URL` = URL do preview.
- MongoDB local é **standalone** (sem replica set) → transações caem no fallback do app no preview.

## Rodada atual (itens 1, 2, 3 do PLANO)
### 1. R7 — senha do usuário QA versionada → lida de env
- `KREDOR_QA_SENHA` agora é a fonte da senha em:
  - backend/tests/e2e_centavos.sh, e2e_aberto.sh (`: "${KREDOR_QA_SENHA:?...}"`)
  - backend/tests/test_fase1_centavos_regressao.py (sem a var → `pytest.skip`)
  - backend/tests/test_n1_refactor_regression.py (idem)
- Senha antiga (`Kq!2026-...`) removida dos arquivos versionados. Senha nova rotacionada, **não** versionada.
- Usuário `qa.kredor@kredor.com.br` (re)criado no preview: plano enterprise, ativo, email verificado.

### 2. 3.5(c) — catch só com console.error: 92 → 0
- Toast (operação-específica) inserido/reordenado em todos os `catch` de `frontend/src/pages/`.
- Import de `toast` (de `hooks/use-toast`) adicionado onde faltava. Build exit=0, nenhum data-testid removido.

### 3. 2.3 — queries em laço (N+1): 45 → 35
- `routes/analise.py`: laço de análise de clientes 4→0 (batch $in + aggregate $group/$max).
- `routes/emprestimos.py`: 8→2 (lixeira cliente_nome, juros de abertos na listagem, resumo abertos,
  criar aberto insert_many, listar_parcelas bulk_write). Restam 2 dentro de transação (incorporação) — deixados de propósito.

## Verificações (provas)
- git grep senha antiga → vazio. 3.5(c) → 0. 2.3 → 35. checar_session_em_transacao → exit 0.
- pytest (fase1 + n1) com KREDOR_QA_SENHA → **23 passed**.
- build frontend → exit 0.
- e2e_recibo_parcial.py → **NÃO executado** (exige DB com replica set; ambiente é standalone).
- testing_agent (backend): 100% — nenhum regressão do refactor N+1.

## Backlog / próximas rodadas (NÃO nesta)
- 2.3 restantes (35): clientes.py, parcelas.py, superadmin.py, whatsapp*.py, notificacao_service, plano_service,
  regua_cobranca_service, email_jobs, emprestimos_abertos_job, inadimplencia_job, resumo_whatsapp_job + os 2 em transação.
- 2.2 (datas: 318 isoformat / 30 utcnow) — inclui bug pré-existente: POST /api/emprestimos sem_prazo com
  data_inicio naive → 500 (comparação naive vs aware em emprestimos.py:~223).
- 3.5(d) (11 arquivos > 800 linhas).

# Kredor / GestorCred — PRD & Progresso

## Contexto
Sistema de gestão de empréstimos a juros (FastAPI + React + MongoDB). Projeto importado.
App no ar via supervisor (backend 8001, frontend 3000, mongodb). DB: `gestorcred`.

## Setup feito (10/09/2026)
- .env de backend/frontend criados com os valores fornecidos pelo usuário + URL de preview.
- Serviços no ar; landing carrega OK.
- Banco anexado NÃO foi recebido — `gestorcred` está vazio (só seeds padrão). Import pendente.

## Execução do PLANO_CORRECOES.md
### 3.4.1 — Teto de prazo (DoS) ✅ CONCLUÍDA e verificada
- `models/emprestimo.py`: `Field(ge/le)` em SimulacaoRequest e EmprestimoCreate
  (principal <= R$1bi; prazo_meses<=600, prazo_semanas<=2600, prazo_dias<=18250).
- `tests/test_simulacao_teto.py` (6 passed). Critérios: 422 acima do teto, 200 válido, <1s/<50MB.

### 3.5 — Frontend (parcial)
- ✅ Critério 2: axios/fetch em src/pages/ = 0 (27 → 0). Todas as chamadas movidas para src/api/api.js
  (novos módulos: backupAPI, portalAPI, timezoneAPI, cepAPI; extensões em assinaturasAPI e adminTransacoesAPI).
- ✅ Critério 3: process.env.REACT_APP_BACKEND_URL em src/ = 0.
- ⛔ Critério 1: maior arquivo < 800 linhas — NÃO feito (Configuracoes.js=2442, Consultas=1621,
  Pagamentos=1585, Clientes=1514). Requer split cuidadoso multi-arquivo.

## Backlog (tarefas grandes/arriscadas — exigem passe dedicado c/ testes)
- P1 **2.2** Datas como Date do BSON (318 isoformat + 37 utcnow). RISCO: datas gravadas E
  consultadas como string; troca naive→aware gera TypeError em comparações (ex.: cupons em
  admin_transacoes.py). Precisa mudança coordenada storage+filtros+migração+leitura.
- P1 **2.3** N+1 (~45 laços) → agregação. Depende de 2.2. Falta o checker scripts/checar_query_em_laco.py.
- P2 **3.3** Imports dentro de função (177 → <20). Existem por ciclo de import; hoist cego quebra o boot.
- P2 **3.5 crit 1** Split de componentes > 800 linhas.

## Regras permanentes seguidas: R9 (sem escopo extra), R10 (prova por critério).

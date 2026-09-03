# GestorCred — Sistema de Gestão de Empréstimos

## Contexto
Projeto existente (React + FastAPI + MongoDB) importado e colocado em execução no ambiente. O banco de dados foi restaurado a partir do backup anexado `backup-20260902-182538.tar.gz`.

## Problem Statement (original)
"importe um projeto, coloque para rodar e importe o banco anexado."

## O que foi feito (data: 2026)
- **Banco importado**: `mongorestore` do dump para a database `gestorcred` (8459 documentos: 43 clientes, 81 empréstimos, 307 parcelas, 195 pagamentos, 4 usuários, WhatsApp, checkout/transações, etc).
- **Configuração de ambiente**: criados `backend/.env` (MONGO_URL local, DB_NAME=gestorcred, JWT, FIELD_ENCRYPTION_KEY, EMERGENT_LLM_KEY, STRIPE_API_KEY=sk_test_emergent) e `frontend/.env` (REACT_APP_BACKEND_URL do preview).
- **Serviços**: backend (uvicorn/supervisor :8001) e frontend (:3000) rodando; health `/api/` = 200; login validado end-to-end.
- **Correções de lint (32 bloqueios pré-existentes)**: bare `except` → `except Exception`, imports/funções duplicadas, star import em `suporte.py`, chave `$ne` duplicada, bug de serialização de ObjectId no export de transações.
- **Object Storage (Emergent)**: `routes/upload.py` (anexos do chat de suporte) e importação de backup em `routes/backup.py` migrados de disco local para object storage (durável em produção); chamadas de rede envolvidas em `asyncio.to_thread`.
- **Fix regressão**: `/api/backup/listar` agora inclui backups importados no object storage (via `backup_logs`).

## Credenciais
- Admin: `diego.haidmann@gmail.com` / `Admin@2026` (senha redefinida nesta importação; a original era desconhecida). Ver `/app/memory/test_credentials.md`.

## Status de testes
- 23/23 casos de backend (pytest) passando: auth, listagem de clientes/empréstimos, parcelas, relatórios, admin transações, suporte, upload→object storage→serve. Fluxo de importação de backup validado (não destrutivo).

## Observações / Limitações
- Campos criptografados (ex.: CPF em `clientes`) foram gravados com a `FIELD_ENCRYPTION_KEY` original de produção, desconhecida. Com a chave de dev atual, esses campos podem não descriptografar corretamente. Se necessário, informar a chave original.
- Integrações de WhatsApp / Stripe / SMTP presentes mas sem credenciais reais (desativadas em dev).

## Backlog / Próximos passos (P1/P2)
- Validação de content-type por magic-bytes e limite de tamanho antes de bufferizar no upload (P2).
- Consolidar os dois endpoints de export em `admin_transacoes.py` (P2).
- Configurar credenciais reais de integrações quando o usuário fornecer (P1).

## Changelog
- **set/2026 — Fix Score de Clientes**: score não era recalculado (todos os 43 clientes sem `score_atual`, apareciam como 60 em `/analise/clientes`). Adicionado recálculo automático ao registrar e estornar pagamento (`routes/pagamentos.py`) e no job de inadimplência (`jobs/inadimplencia_job.py`); backfill dos clientes existentes. Corrigidos 2 bugs colaterais em `GET /api/analise/clientes`: `ultimo_pagamento` agora é por cliente (era global) e a listagem passou a aplicar filtro de soft-delete (não lista clientes excluídos). Verificado por testing agent (7/7) + curl: scores variam de 27 a 94 (A–E).
- **set/2026 — atuasetembro.md**: roadmap repriorizado após diagnóstico dos dados (negócio 100% empréstimo; módulo de Vendas removido do escopo; P0 = Consultas de crédito).
- **set/2026 — iniciar.sh**: script para subir todos os serviços com health-check.

## [2026-09-03] Bug fix: empréstimos abertos pararam de gerar parcelas
- **Sintoma**: empréstimo aberto (sem_prazo, semanal, apenas_juros) do cliente Rodrigo parou na parcela #21.
- **Causa raiz**: ao atingir 30+ dias de atraso, `inadimplencia_job` muda status 'ativo'->'inadimplente'. O `job_gerar_parcelas_emprestimos_abertos` e o fluxo de pagamento (routes/pagamentos.py) só consideravam status 'ativo', então paravam de gerar as parcelas de juros.
- **Fix**: incluído 'inadimplente' na query do job ({$in:['ativo','inadimplente']}) e na condição do pagamento. Só 'quitado'/'cancelado' param de gerar. Adicionado guard por empréstimo (data_inicio inválida não aborta o loop).
- **Validação**: testing_agent 8/8 testes OK. Backfill executado: Rodrigo agora com 24 parcelas (#24 pendente venc 2026-09-09).

## [2026-09-03] 4 melhorias de Empréstimos Abertos
1. **Serviço compartilhado**: services/parcela_service.py (inserir_parcela_juros_aberto) usado pelo job e pelo pagamento — fim da lógica duplicada. Idempotente via índice único parcial.
2. **Alerta de Inadimplência**: inadimplencia_job cria notificação (tipo 'atraso', prioridade 'alta', link /emprestimos/{id}) ao marcar empréstimo como inadimplente. Não recria para os já inadimplentes.
3. **Painel de Abertos**: GET /api/emprestimos/abertos/resumo + página /emprestimos/abertos (menu Empréstimos > Abertos (Juros)). Mostra juros gerado/recebido/em aberto e próxima parcela em aberto por empréstimo.
4. **Reversão Automática**: pagamento reverte inadimplente->ativo quando não há parcela vencida com saldo em aberto.
- **Bugs pré-existentes corrigidos em routes/pagamentos.py**: (a) status marcava 'pago' com pagamento parcial (comparava saldo restante em vez do total devido); (b) reversão contava só status=='atrasado', então pagamento parcial revertia indevidamente.
- **Validação**: testing_agent 19/19 testes backend OK; frontend 100%.
- Pendências opcionais (backlog): unificar regra de inadimplência (30 dias) entre job e pagamento; otimizar /abertos/resumo (N+1); corrigir exibição de taxa/total na tela de detalhe de empréstimos sem_prazo.

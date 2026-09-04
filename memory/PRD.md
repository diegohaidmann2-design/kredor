# GestorCred — Sistema de Gestão de Empréstimos

## Contexto
Projeto existente (React + FastAPI + MongoDB) importado e colocado em execução no ambiente. O banco de dados foi restaurado a partir do backup anexado `backup-20260902-182538.tar.gz`.

## Problem Statement (original)
"importe um projeto, coloque para rodar e importe o banco anexado."

## O que foi feito (data: 2026)
- **Simulação /simulacao (jun/2026)**: (1) modo **Simples** — informa valor emprestado + valor a receber → calcula juros (R$ e %) automaticamente; opção "Dividir em N pagamentos" com frequência Diária/Semanal/Mensal e cronograma; atalhos 10/20/30 dias (cálculo 100% no cliente). (2) Nova periodicidade **Diária** no backend (SimulacaoRequest/Response com taxa_juros_diaria/prazo_dias; calculos.py; POST /api/emprestimos/simular) e no modo Avançado. Validado: backend 5/5, frontend 100%.
- **Melhorias tela /pagamentos (jun/2026)**: mini-card por empréstimo com referência (#REF), ícone/cor por tipo (Juros=roxo/Repeat, Parcelado=azul/Layers), recolher/expandir, barra de progresso "X/N pagas" e botão "Cobrar tudo".
- **Fix empréstimo aberto Rodrigo**: rodado job de geração de parcelas (backfill #22/#23/#24) após restauração do backup.
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

## [2026-09-03] 4 melhorias (rodada 2)
1. **Regra Unificada (30 dias)**: services/inadimplencia_service.py é fonte única (limiar 30 dias + fórmula de saldo com multa/juros de mora). Job e fluxo de pagamento usam a MESMA regra via recalcular_status_emprestimo/esta_inadimplente → status não oscila. Corrigido bug em que o job ignorava multa/mora e revertia indevidamente.
2. **Cobrança no Painel**: botão "Pagar" em cada card de /emprestimos/abertos abre modal e registra pagamento (POST /api/pagamentos) sem sair da tela; endpoint /abertos/resumo agora expõe proxima_parcela.parcela_id.
3. **Detalhe do Aberto**: EmprestimoDetalhes.js corrigido p/ sem_prazo — taxa "X% por semana/ao mês" (nunca vazia), "Juros por período", "Sem prazo (apenas juros)", "Capital Devedor" (não negativo). Dias de atraso ocultos em parcelas pagas.
4. **Resumo no WhatsApp**: jobs/resumo_whatsapp_job.py (JOB 14 no scheduler, segunda 08:30) envia ao gestor (via Evolution API / whatsapp_service) resumo de empréstimos ativos, juros em aberto, parcelas vencidas e a vencer em 7 dias. DEPENDE de WhatsApp conectado (whatsapp_conexoes status 'conectado'); neste banco não há conexão, então executa sem enviar (conexoes=0).
- **Validação**: testing_agent 35/35 testes backend OK; frontend validado (painel+modal, detalhe aberto e prazo fixo).

## [2026-09-03] Cobrança WhatsApp no Painel de Abertos
- Botão "Cobrar" (data-testid btn-cobrar-{id}) em cada card de /emprestimos/abertos, habilitado só quando há parcela vencida (dias_atraso>0). Reusa endpoint existente POST /api/whatsapp/enviar-cobranca-parcela/{parcela_id} (busca cliente, telefone, template, envia via Evolution API com anti-spam). Toast de feedback + stopPropagation (não navega ao detalhe).
- DEPENDE de WhatsApp conectado; sem conexão exibe toast "WhatsApp não está conectado".
- Validação: testing_agent frontend 100% (4/4 cenários). Fix cosmético: pb-24 na lista p/ toast não sobrepor último card.

---
## Iteração — set/2026 (pós import do banco real)

### Contexto
Projeto importado. Recriados os .env, instaladas dependências, restaurado banco real (backup-20260902-182538, 8459 docs). Admin: diego.haidmann@gmail.com / Admin@2026.

### Roadmap escolhido pelo usuário (atuasetembro.md) — 1 item por vez
1. [FEITO] Agenda / Calendário de Cobrança
2. [PRÓXIMO] Cadastro público do cliente + fluxo de aprovação
3. [DEPOIS] Consultas de crédito CPF/CNPJ (provedor: Boa Vista) — requer credenciais/API

### Implementado nesta iteração
- **Agenda de Cobrança** (`/agenda`): página nova com visão Calendário mensal + visão Lista por período.
  - Buckets de resumo: Atrasadas / Vencem hoje / Próximos 7 dias (contagem + valor), clicáveis para cobrar em lote.
  - Calendário: navegação de mês, botão Hoje, badges de contagem/valor por dia, seleção de dia abre painel com as parcelas.
  - Ações: cobrar 1 parcela (WhatsApp), cobrar dia/bucket em lote (cobrar-em-massa), link wa.me direto, ver empréstimo.
  - Reusa GET /api/parcelas/pendentes, POST /api/whatsapp/enviar-cobranca-parcela/{id}, POST /api/parcelas/cobrar-em-massa.
  - Arquivos: frontend/src/pages/Agenda.js, rota em App.js, item nav-agenda em Sidebar.js.
  - Validado 100% pelo testing agent (iteration_33). WhatsApp offline no ambiente => cobranças mostram modal de erro amigável (esperado).

### Implementado — Item 2: Cadastro Público + Aprovação (set/2026)
- **Link público por conta**: dono gera/regenera um token (`/api/cadastro-publico/link`), URL `/cadastro/{token}`.
- **Página pública** (`/cadastro/:token`, sem login): cliente preenche ficha (nome, CPF/CNPJ, telefone, email, endereço, obs) e envia.
- **Fluxo de aprovação** (`/aprovacoes`): abas Pendentes/Aprovados/Rejeitados; aprovar cria o cliente (origem=cadastro_publico) + gera código de portal; rejeitar marca a ficha; copiar/abrir/regenerar link.
- Coleção nova: `solicitacoes_cadastro`. Notifica o dono a cada nova ficha.
- Arquivos: backend/routes/cadastro_publico.py; frontend pages CadastroPublico.js, Aprovacoes.js; api cadastroPublicoAPI; rotas em App.js; nav-aprovacoes em Sidebar.js.
- Validado 100% (backend+frontend) pelo testing agent (iteration_34). Dados de QA removidos após teste.
- Nota: backend/.env APP_URL deve permanecer igual à URL pública do front (usado para montar o link).

### Roadmap status
1. [FEITO] Agenda de Cobrança
2. [FEITO] Cadastro público + aprovação
3. [PENDENTE] Consulta de crédito CPF/CNPJ via Boa Vista (requer credenciais da API)

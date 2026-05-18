# GestorCred - Sistema de Gestao de Emprestimos

## Problema Original
Sistema full-stack (React + FastAPI + MongoDB) para gestao de emprestimos pessoais, com funcionalidades de controle de clientes, emprestimos, parcelas, pagamentos, notificacoes via WhatsApp, e painel administrativo.

## Arquitetura
- **Frontend**: React.js (porta 3000)
- **Backend**: FastAPI (porta 8001)
- **Database**: MongoDB
- **Servicos**: supervisorctl para gerenciamento

## Funcionalidades Implementadas

### Core
- Dashboard com metricas financeiras
- Gestao de clientes, emprestimos, parcelas e pagamentos
- Simulacao de emprestimos
- Relatorios e exportacao de dados
- Contratos
- Sistema de assinatura com planos
- Portal do cliente (self-service)
- Equipe e convites
- Assistente IA (rule-based interno)
- Notificacoes e suporte

### Juros de Mora
- Calculo automatico de juros e multas em parcelas atrasadas
- Job a cada 6h via apscheduler

### WhatsApp Integration
- Envio de confirmacao de pagamento
- Anti-spam, auditoria

### Admin/Super Admin
- Gestao de usuarios, assinaturas, transacoes, cupons
- Jobs & Scheduler, Auditoria

### Excluir Parcela
- Soft delete via DELETE /api/parcelas/{id}

### Editar Emprestimo Sem Prazo (2026-04-08)
- Modal respeita sem_prazo e periodicidade
- Backend EmprestimoUpdate aceita campos semanais

### Fluxo Emprestimo Sem Prazo — Correcoes (2026-04-08)
- Bugs 1-8 corrigidos (taxa juros, variavel inexistente, soft-delete, etc)

### Verificacao Completa Sem Prazo (2026-06-07)
- Testing agent confirmou 100% backend (15/15 testes) e frontend

### Prorrogacao de Emprestimos (2026-04-10)
- Endpoint POST /api/emprestimos/{id}/prorrogar implementado
- Funciona com modalidade "apenas_juros" (capital no final)
- Frontend: Modal com input de periodos e resumo (em EmprestimoDetalhes.js)

### SEO Rebranding (2026-04-11)
- Rebranding completo de JuroFacil para GestorCred

### MercadoPago Removal (2026-04-11)
- Removido completamente do codebase
- Endpoints retornam HTTP 410 Gone

### SyncPay PIX Integration E2E (2026-04-12)
- POST /api/assinaturas/checkout-syncpay
- GET /api/assinaturas/syncpay-status/{id}
- POST /api/assinaturas/webhook-syncpay
- SyncPay v2 API: auth-token, cash-in, transaction/{id}
- Testado E2E: 100% backend + 100% frontend

### Checkout Redesign Alta Conversao (2026-04-13)
- Layout 2 colunas: form esquerda + resumo sticky direita com glassmorphism
- Upgrade mode: card compacto do usuario logado com badge "Verificado"
- Publico: form 2 colunas com campos Nome, Email, Senha, CPF, Telefone
- Payment method cards com visual PIX/Boleto/Cartao
- CTA botao grande verde com preco + icone cadeado
- Trust signals: criptografia + pagamento seguro
- Cupom de desconto inline
- Design Swiss/High-Contrast dark theme
- Testado E2E: 100% backend + 100% frontend

## Gateways de Pagamento
- **Asaas** (PIX/Boleto/Cartao) - Configuravel via painel admin
- **SyncPay** (PIX apenas) - Integracao completa E2E
- **MercadoPago** - REMOVIDO (HTTP 410 Gone)

### Reativacao do Ambiente (2026-05-08)
- Backend e frontend estavam parados (pod pausado) - reiniciados via supervisorctl
- Banco MongoDB estava vazio (0 usuarios) - seeder executado com sucesso
- 3 usuarios criados (diego.haidmann, admin@gestorcerd, usuario@teste)
- Login validado E2E (3/3 contas), dashboard renderizando, indices criados
- Scheduler de jobs ativo (11 jobs agendados)

### Bug Fixes Sessao (2026-05-08)
- Bug 1: handleExcluirParcela is not defined em /pagamentos -> adicionado prop em ParcelaRow (3 lugares)
- Bug 2: Total com Juros nao atualizava ao excluir parcela em emprestimo aberto -> adicionado filtro deleted no agregador (emprestimos.py:386, 1003)
- Bug 3: Erro 500 em GET /api/emprestimos/{id}/parcelas para parcelas legacy -> tornados valor_principal/saldo_devedor opcionais com default 0
- Bug 4: Em emprestimo aberto, pagamento auto-gerava parcela sem checar se ja havia pendente -> adicionada verificacao outras_pendentes==0 em pagamentos.py

### Feature: Amortizacao de Capital (2026-05-08)
- Endpoint POST /api/emprestimos/{id}/amortizar
- Campos: valor_amortizacao, metodo_pagamento, observacoes, recalcular_juros (bool)
- Logica: reduz valor_principal, registra pagamento tipo='amortizacao', recalcula juros das parcelas pendentes opcionalmente, quita automaticamente quando capital chega a 0
- UI: botao "Amortizar Capital" no menu de acoes do empréstimo aberto
- Modal com campos do valor + metodo + observacoes
- Confirmacao com botoes "Sim, recalcular"/"Nao, manter juros" para escolher se recalcula juros futuros

### Foco em Pagamentos Pendentes / Inadimplência (2026-05-17)
**Bug Fix Critico:**
- total_juros_recebidos no dashboard estava usando heuristica `total_pagamentos * 0.3` (chutado). Corrigido para somar valor_juros REAL das parcelas com status pago/paga.

**Dashboard - Novos campos no GET /api/dashboard:**
- valor_em_atraso (R$ total devido pelas parcelas atrasadas, com multa+mora)
- a_receber_hoje / a_receber_semana / a_receber_mes
- recebido_mes_atual (somatorio real dos pagamentos do mes corrente)
- proximo_recebimento (proxima parcela a vencer)
- aging_atrasos (faixas 1-7d, 8-15d, 16-30d, 30+d com valor e quantidade)
- top_inadimplentes (top 10 clientes ordenados por valor_devido com telefone para cobranca)

**Dashboard - Frontend:**
- Componente PagamentosPendentesSection.js: 5 cards coloridos (atraso vermelho, hoje ambar, 7d azul, mes violeta, recebido verde)
- Card "Proximo Recebimento" destacado
- Gráfico de barras de Aging dos atrasos
- Lista "Top Inadimplentes" com botão Cobrar -> navega para /pagamentos?cliente={nome}

**Pagamentos - Backend:**
- DELETE /api/pagamentos/{id} (estorno): soft-delete + reverte valor_pago da parcela + recalcula status + reverte status do emprestimo (quitado->ativo). Bloqueia estorno de tipo='amortizacao'.
- POST /api/parcelas/cobrar-em-massa: aceita lista de parcela_ids (max 50). Chama enviar-cobranca-parcela para cada. Retorna {enviadas, falhas, detalhes}. Marca ultima_cobranca_em.
- Novo campo `ultima_cobranca_em` nas parcelas pendentes (timestamp da ultima cobranca via WhatsApp).
- Campo `tipo` no modelo Pagamento ('pagamento' | 'amortizacao').

**Pagamentos - Frontend:**
- Card "Total a Receber" agora considera multa + juros de mora
- Card "Em Atraso (valor)" mostra valor monetario em vermelho
- Card "Taxa de Recebimento" substituiu "Media por Pagamento"
- Tab default agora e "Parcelas Pendentes"
- Barra de Acoes em Massa: checkbox "Selecionar todas" + botao "Cobrar via WhatsApp" em lote
- Cada parcela tem checkbox + badge "Cobrado ha Xd" (se ultima_cobranca_em preenchido)
- Botoes inline "Pagar" e "Cobrar" sem precisar abrir dropdown
- Suporte a query params ?filtro=atrasado&cliente=Nome
- Historico: filtro por cliente + exportar CSV (UTF-8 BOM, separador `;`)
- Historico: botao "Estornar" + badge "AMORT." nas amortizacoes

**Testing:**
- 15/15 testes backend OK (iteration_15.json)
- 35/35 validacoes frontend OK (iteration_16.json)

## Backlog / Proximas Tarefas
- P0: Sistema de Backup & Restore implementado (ver abaixo)
- P1: Validar webhook SyncPay callback end-to-end
- P1: Refatorar Pagamentos.js (arquivo extenso)
- P2: Melhorar acessibilidade do botao Prorrogar (tirar do dropdown)
- P2: Limpar warnings de linting em assinaturas.py
- P2: Em /emprestimos/{id} (detalhe), recalcular dinamicamente "Total com Juros" para emprestimo aberto (hoje mostra R$0 enquanto a listagem mostra valor correto)
- P2: Pagina /pagamentos -> mostrar tambem amortizacoes no historico (separadas)
- Aguardando novas instrucoes do usuario

### Sistema de Backup & Restore (2026-05-18)
**Camada 1 — Backup Automático (a cada 6h via APScheduler):**
- Job `backup_automatico` registrado no scheduler (IntervalTrigger 6h)
- Usa mongodump para fazer dump completo do banco
- Comprime em .tar.gz e salva em /app/backups/
- Mantém últimos 30 backups rotativos automaticamente
- Logs salvos em collection `backup_logs`

**Camada 2 — Backup Manual:**
- POST /api/backup/criar - gera backup imediatamente
- Botão "Fazer Backup Agora" no painel admin (/admin/backup)
- Exibe tamanho do arquivo e timestamp

**Camada 3 — Restore com 1 Clique:**
- GET /api/backup/listar - lista todos os backups disponíveis
- POST /api/backup/restaurar/{nome} - restaura banco (com --drop)
- Botão de restore com confirmação inline na UI
- GET /api/backup/download/{nome} - download via autenticação JWT (header)
- DELETE /api/backup/deletar/{nome} - remove arquivo de backup
- GET /api/backup/logs - histórico de operações (backup/restore)
- Item "Backup & Restore" no menu Super Admin da sidebar

**Correção de Bug (detectada pelo testing agent):**
- AuthContext não exportava `token` no Provider value — corrigido

## Notas Tecnicas
- Credenciais: ver /app/memory/test_credentials.md
- A integracao WhatsApp depende de configuracao externa
- SyncPay API base: https://api.syncpayments.com.br

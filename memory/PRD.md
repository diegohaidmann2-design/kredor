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

## Backlog / Proximas Tarefas
- P1: Validar webhook SyncPay callback end-to-end
- P1: Refatorar Pagamentos.js (arquivo extenso)
- P2: Melhorar acessibilidade do botao Prorrogar (tirar do dropdown)
- P2: Limpar warnings de linting em assinaturas.py
- Aguardando novas instrucoes do usuario

## Notas Tecnicas
- Credenciais: ver /app/memory/test_credentials.md
- A integracao WhatsApp depende de configuracao externa
- SyncPay API base: https://api.syncpayments.com.br

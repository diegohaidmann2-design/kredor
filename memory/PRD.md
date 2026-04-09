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
- Assistente IA
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
- **Bug 1 FIXED**: Job usava taxa_juros_mensal hardcoded -> agora respeita periodicidade
- **Bug 2 FIXED**: Endpoint /quitar referenciava variavel inexistente juros_mensal -> juros_periodo
- **Bug 3 FIXED**: Filtro soft-delete inconsistente deleted_at -> deleted
- **Bug 4 FIXED**: Job esperava 7 dias -> agora gera no dia seguinte ao vencimento
- **Bug 5 FIXED**: Job ignorava status "atrasado" -> incluido na condicao
- **Bug 6 FIXED**: Job nao marcava parcela como atrasada -> agora marca antes de gerar nova
- **Bug 7 FIXED**: Endpoint /quitar nao marcava emprestimo como "quitado" -> agora marca
- **Bug 8 FIXED**: Auditoria do /quitar faltava parametro detalhes

### Verificacao Completa Sem Prazo (2026-06-07)
- Testing agent confirmou 100% backend (15/15 testes) e frontend
- Edit modal oculta campo prazo para sem_prazo
- PUT aceita update sem prazo_meses/prazo_semanas para sem_prazo
- /quitar valida corretamente e rejeita emprestimos nao-sem_prazo ou ja quitados
- Criacao auto-gera primeira parcela com valor_principal=0 (apenas juros)
- Background job respeita periodicidade (semanal/mensal)

## Backlog / Proximas Tarefas
- P1: Refatorar Pagamentos.js (arquivo extenso, candidato a modularizacao)
- Aguardando novas instrucoes do usuario

## Notas Tecnicas
- Credenciais: ver /app/memory/test_credentials.md
- A integracao WhatsApp depende de configuracao externa
- Pagamentos.js e extenso — candidato a refatoracao futura

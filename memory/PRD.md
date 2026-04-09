# GestorCred - Sistema de Gestão de Empréstimos

## Problema Original
Sistema full-stack (React + FastAPI + MongoDB) para gestão de empréstimos pessoais, com funcionalidades de controle de clientes, empréstimos, parcelas, pagamentos, notificações via WhatsApp, e painel administrativo.

## Arquitetura
- **Frontend**: React.js (porta 3000)
- **Backend**: FastAPI (porta 8001)
- **Database**: MongoDB
- **Serviços**: supervisorctl para gerenciamento

## Funcionalidades Implementadas

### Core
- Dashboard com métricas financeiras
- Gestão de clientes, empréstimos, parcelas e pagamentos
- Simulação de empréstimos
- Relatórios e exportação de dados
- Contratos
- Sistema de assinatura com planos
- Portal do cliente (self-service)
- Equipe e convites
- Assistente IA
- Notificações e suporte

### Juros de Mora
- Cálculo automático de juros e multas em parcelas atrasadas
- Job a cada 6h via apscheduler

### WhatsApp Integration
- Envio de confirmação de pagamento
- Anti-spam, auditoria

### Admin/Super Admin
- Gestão de usuários, assinaturas, transações, cupons
- Jobs & Scheduler, Auditoria

### Excluir Parcela
- Soft delete via DELETE /api/parcelas/{id}

### Editar Empréstimo Sem Prazo (2026-04-08)
- Modal respeita sem_prazo e periodicidade
- Backend EmprestimoUpdate aceita campos semanais

### Fluxo Empréstimo Sem Prazo — Correções (2026-04-08)
- **Bug 1 FIXED**: Job usava taxa_juros_mensal hardcoded → agora respeita periodicidade
- **Bug 2 FIXED**: Endpoint /quitar referenciava variável inexistente juros_mensal → juros_periodo
- **Bug 3 FIXED**: Filtro soft-delete inconsistente deleted_at → deleted
- **Bug 4 FIXED**: Job esperava 7 dias → agora gera no dia seguinte ao vencimento
- **Bug 5 FIXED**: Job ignorava status "atrasado" → incluído na condição
- **Bug 6 FIXED**: Job não marcava parcela como atrasada → agora marca antes de gerar nova
- **Bug 7 FIXED**: Endpoint /quitar não marcava empréstimo como "quitado" → agora marca
- **Bug 8 FIXED**: Auditoria do /quitar faltava parâmetro detalhes

## Backlog / Próximas Tarefas
- Nenhuma tarefa pendente. Aguardando instruções do usuário.

## Notas Técnicas
- Credenciais: ver /app/memory/test_credentials.md
- A integração WhatsApp depende de configuração externa
- Pagamentos.js é extenso — candidato a refatoração futura

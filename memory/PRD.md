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

### Juros de Mora (Implementado)
- Cálculo automático de juros e multas em parcelas atrasadas
- Job diário via apscheduler para atualização

### WhatsApp Integration (Implementado)
- Envio de confirmação de pagamento
- Configuração de conexão WhatsApp
- Anti-spam
- Sistema de auditoria (logs de mensagens enviadas)

### Admin/Super Admin
- Gestão de usuários, assinaturas, transações, cupons
- Jobs & Scheduler
- Auditoria (Logs Sistema + Logs WhatsApp)

### Excluir Parcela (Implementado)
- Soft delete via DELETE /api/parcelas/{id}
- Validações: ownership, parcela não paga, segurança

### Editar Empréstimo Sem Prazo (Implementado - 2026-04-08)
- Modal de edição agora respeita `sem_prazo` e `periodicidade`
- Campo de prazo oculto quando sem_prazo=true
- Labels de taxa ajustados (mensal/semanal)
- Backend EmprestimoUpdate aceita periodicidade, taxa_juros_semanal, prazo_semanas, sem_prazo

## Correções Recentes
- **2026-04-08**: Corrigido modal EditarEmprestimoModal que exigia prazo em empréstimos sem prazo. Adicionado suporte a periodicidade semanal e campos sem_prazo no backend EmprestimoUpdate.

## Backlog / Próximas Tarefas
- Nenhuma tarefa pendente. Aguardando instruções do usuário.

## Notas Técnicas
- Credenciais: ver /app/memory/test_credentials.md
- A integração WhatsApp depende de configuração externa
- Pagamentos.js é extenso — candidato a refatoração futura

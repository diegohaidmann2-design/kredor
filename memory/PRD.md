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
- Serviço: `backend/src/services/calculations/late_fee_calculator.py`

### WhatsApp Integration (Implementado)
- Envio de confirmação de pagamento
- Configuração de conexão WhatsApp
- Anti-spam
- Sistema de auditoria (logs de mensagens enviadas)

### Admin/Super Admin
- Gestão de usuários, assinaturas, transações, cupons
- Jobs & Scheduler
- Auditoria (Logs Sistema + Logs WhatsApp) - submenu funcional na sidebar

## Correções Recentes
- **2026-02-XX**: Corrigido submenu "Auditoria" na sidebar admin que não expandia. Causa: `AdminNavItem` não suportava submenus (era apenas um Link simples). Solução: adicionada lógica de expansão de submenu com estilo amber/admin.

## Backlog / Próximas Tarefas
- Nenhuma tarefa pendente solicitada pelo usuário. Aguardando novas instruções.

## Notas Técnicas
- Credenciais admin: admin@gestorcerd.com / admin123
- A integração WhatsApp depende de configuração externa (notificacao_service_v2)
- O arquivo Pagamentos.js é extenso e candidato a refatoração futura

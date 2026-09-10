"""
Serviço de Onboarding - Gerenciamento do progresso de novos usuários
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.onboarding_service")

from datetime import datetime, timezone
from typing import Optional


class OnboardingService:
    """Serviço para gerenciar o onboarding de novos usuários"""
    
    # Configuração das tarefas do onboarding
    TASKS = {
        "perfil_completo": {
            "title": "Complete seu perfil",
            "description": "Adicione suas informações básicas",
            "points": 10,
            "action": "/perfil",  # ✅ Agora aponta para /perfil (usuários comuns)
            "icon": "User"
        },
        "primeiro_cliente": {
            "title": "Adicione seu primeiro cliente",
            "description": "Cadastre um cliente para começar",
            "points": 20,
            "action": "/clientes",
            "icon": "Users"
        },
        "primeiro_emprestimo": {
            "title": "Crie seu primeiro empréstimo",
            "description": "Configure um empréstimo para um cliente",
            "points": 30,
            "action": "/emprestimos",
            "icon": "DollarSign"
        },
        "primeiro_pagamento": {
            "title": "Registre um pagamento",
            "description": "Marque uma parcela como paga",
            "points": 20,
            "action": "/pagamentos",
            "icon": "CreditCard"
        },
        "primeiro_contrato": {
            "title": "Gere seu primeiro contrato",
            "description": "Crie um contrato PDF para um empréstimo",
            "points": 10,
            "action": "/contratos",
            "icon": "FileText"
        },
        "configuracoes": {
            "title": "Configure suas preferências",
            "description": "Ajuste as configurações do sistema",
            "points": 10,
            "action": "/perfil",  # ✅ Usuários comuns vão para /perfil
            "icon": "Settings"
        }
    }
    
    # Steps do tour interativo
    TOUR_STEPS = [
        {
            "step": 1,
            "target": "#sidebar-clientes",
            "title": "👥 Gestão de Clientes",
            "content": "Aqui você cadastra e gerencia todos os seus clientes. Você pode adicionar informações como CPF, telefone e endereço.",
            "placement": "right"
        },
        {
            "step": 2,
            "target": "#sidebar-emprestimos",
            "title": "💰 Empréstimos",
            "content": "Crie empréstimos com 4 métodos de cálculo: Juros Simples, Compostos, Price e SAC. O sistema calcula automaticamente as parcelas.",
            "placement": "right"
        },
        {
            "step": 3,
            "target": "#sidebar-pagamentos",
            "title": "💳 Pagamentos",
            "content": "Registre pagamentos de parcelas e acompanhe o histórico completo de cada empréstimo.",
            "placement": "right"
        },
        {
            "step": 4,
            "target": "#sidebar-contratos",
            "title": "📄 Contratos",
            "content": "Gere contratos profissionais em PDF com 3 modelos diferentes: padrão, com garantia e personalizado.",
            "placement": "right"
        },
        {
            "step": 5,
            "target": "#sidebar-relatorios",
            "title": "📊 Relatórios",
            "content": "Exporte relatórios detalhados em PDF ou Excel com análises de empréstimos, pagamentos e inadimplência.",
            "placement": "right"
        },
        {
            "step": 6,
            "target": "#sidebar-analise",
            "title": "🎯 Análise de Score",
            "content": "Acompanhe o score de crédito dos seus clientes (A-E) baseado em pontualidade, atrasos e histórico de pagamentos.",
            "placement": "right"
        },
        {
            "step": 7,
            "target": "#dashboard-stats",
            "title": "📈 Dashboard",
            "content": "Visualize métricas em tempo real: total de empréstimos, recebimentos, parcelas pendentes e muito mais!",
            "placement": "bottom"
        },
        {
            "step": 8,
            "target": "#user-menu",
            "title": "⚙️ Configurações",
            "content": "Acesse suas configurações, notificações e gerenciamento de conta aqui.",
            "placement": "left"
        }
    ]
    
    @staticmethod
    def calculate_progress(tasks: dict) -> int:
        """Calcula o progresso total do onboarding (0-100)"""
        completed_tasks = sum(1 for completed in tasks.values() if completed)
        total_tasks = len(tasks)
        return int((completed_tasks / total_tasks) * 100) if total_tasks > 0 else 0
    
    @staticmethod
    def get_points_earned(tasks: dict) -> int:
        """Calcula os pontos ganhos baseado nas tarefas completadas"""
        points = 0
        for task_key, completed in tasks.items():
            if completed and task_key in OnboardingService.TASKS:
                points += OnboardingService.TASKS[task_key]["points"]
        return points
    
    @staticmethod
    def get_next_task(tasks: dict) -> Optional[dict]:
        """Retorna a próxima tarefa a ser completada"""
        for task_key, task_info in OnboardingService.TASKS.items():
            if not tasks.get(task_key, False):
                return {
                    "key": task_key,
                    **task_info
                }
        return None
    
    @staticmethod
    async def check_task_completion(usuario_id: str, task_key: str, db) -> bool:
        """
        Verifica automaticamente se uma tarefa foi completada
        baseado nos dados do usuário no banco
        """
        try:
            if task_key == "perfil_completo":
                # Perfil completo se tem nome preenchido
                usuario = await db.usuarios.find_one({"id": usuario_id})
                return bool(usuario and usuario.get("nome") and len(usuario.get("nome", "")) > 3)
            
            elif task_key == "primeiro_cliente":
                # Verificar se tem pelo menos 1 cliente
                count = await db.clientes.count_documents({"usuario_id": usuario_id})
                return count > 0
            
            elif task_key == "primeiro_emprestimo":
                # Verificar se tem pelo menos 1 empréstimo
                count = await db.emprestimos.count_documents({"usuario_id": usuario_id})
                return count > 0
            
            elif task_key == "primeiro_pagamento":
                # Verificar se tem pelo menos 1 pagamento
                count = await db.pagamentos.count_documents({"usuario_id": usuario_id})
                return count > 0
            
            elif task_key == "primeiro_contrato":
                # Verificar se tem pelo menos 1 contrato gerado
                # (Contratos são gerados sob demanda, então verificamos se tem empréstimo)
                count = await db.emprestimos.count_documents({"usuario_id": usuario_id})
                return count > 0
            
            elif task_key == "configuracoes":
                # Consideramos "configurado" se mudou alguma preferência
                # Por enquanto, marcamos como true se tem perfil completo
                usuario = await db.usuarios.find_one({"id": usuario_id})
                return bool(usuario and usuario.get("nome"))
            
            return False
        except Exception as e:
            logger.error(f"Erro ao verificar task {task_key}: {e}")
            return False
    
    @staticmethod
    async def auto_check_all_tasks(usuario: dict, db) -> dict:
        """
        Verifica automaticamente todas as tarefas e atualiza o status
        """
        tasks = usuario.get("onboarding_tasks", {})
        updated = False
        
        for task_key in tasks.keys():
            if not tasks[task_key]:  # Se ainda não está completa
                is_complete = await OnboardingService.check_task_completion(
                    usuario["id"], task_key, db
                )
                if is_complete:
                    tasks[task_key] = True
                    updated = True
                    logger.info(f"✅ Auto-completado: {task_key} para usuário {usuario['id']}")
        
        # Se houve mudanças, atualizar no banco
        if updated:
            await db.usuarios.update_one(
                {"id": usuario["id"]},
                {"$set": {"onboarding_tasks": tasks}}
            )
            
            # Verificar se completou 100%
            progress = OnboardingService.calculate_progress(tasks)
            if progress == 100 and not usuario.get("onboarding_completed"):
                from datetime import datetime, timezone
                await db.usuarios.update_one(
                    {"id": usuario["id"]},
                    {"$set": {
                        "onboarding_completed": True,
                        "onboarding_completed_at": datetime.now(timezone.utc).isoformat()
                    }}
                )
        
        return tasks
    
    @staticmethod
    def get_onboarding_status(usuario: dict) -> dict:
        """Retorna o status completo do onboarding do usuário"""
        tasks = usuario.get("onboarding_tasks", {})
        progress = OnboardingService.calculate_progress(tasks)
        points = OnboardingService.get_points_earned(tasks)
        next_task = OnboardingService.get_next_task(tasks)
        
        return {
            "completed": usuario.get("onboarding_completed", False),
            "progress": progress,
            "points": points,
            "total_points": 100,
            "tasks": tasks,
            "next_task": next_task,
            "tour_finished": usuario.get("onboarding_tour_finished", False),
            "current_step": usuario.get("onboarding_step", 0),
            "started_at": usuario.get("onboarding_started_at"),
            "completed_at": usuario.get("onboarding_completed_at")
        }

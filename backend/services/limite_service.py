"""
Serviço de Verificação de Limites por Plano
"""
from datetime import datetime, timezone
from typing import Optional, Tuple
from motor.motor_asyncio import AsyncIOMotorDatabase
from models.plano import get_plano_limites, PlanoLimites


class LimiteService:
    """Serviço para verificar e gerenciar limites de plano"""
    
    def __init__(self, db: AsyncIOMotorDatabase):
        self.db = db
    
    async def obter_limites_usuario(self, usuario_id: str) -> PlanoLimites:
        """Obtém os limites do plano do usuário"""
        usuario = await self.db.usuarios.find_one({"id": usuario_id})
        if not usuario:
            return get_plano_limites("trial")
        
        plano = usuario.get("plano", "trial")
        
        # Tentar buscar plano customizado do banco
        plano_db = await self.db.planos.find_one({"slug": plano})
        if plano_db and plano_db.get("limites"):
            return PlanoLimites(**plano_db["limites"])
        
        # Usar limites padrão
        return get_plano_limites(plano)
    
    async def obter_uso_atual(self, usuario_id: str) -> dict:
        """Obtém o uso atual do usuário"""
        # Contar clientes
        total_clientes = await self.db.clientes.count_documents({"usuario_id": usuario_id})
        
        # Contar empréstimos totais
        total_emprestimos = await self.db.emprestimos.count_documents({"usuario_id": usuario_id})
        
        # Contar empréstimos do mês atual
        inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        emprestimos_mes = await self.db.emprestimos.count_documents({
            "usuario_id": usuario_id,
            "created_at": {"$gte": inicio_mes.isoformat()}
        })
        
        return {
            "clientes": total_clientes,
            "emprestimos": total_emprestimos,
            "emprestimos_mes": emprestimos_mes
        }
    
    async def verificar_limite_clientes(self, usuario_id: str) -> Tuple[bool, str]:
        """
        Verifica se o usuário pode adicionar mais clientes
        Retorna: (pode_adicionar, mensagem)
        """
        limites = await self.obter_limites_usuario(usuario_id)
        uso = await self.obter_uso_atual(usuario_id)
        
        # -1 significa ilimitado
        if limites.max_clientes == -1:
            return True, "OK"
        
        if uso["clientes"] >= limites.max_clientes:
            return False, f"Limite de {limites.max_clientes} clientes atingido. Faça upgrade do seu plano para adicionar mais clientes."
        
        return True, "OK"
    
    async def verificar_limite_emprestimos(self, usuario_id: str) -> Tuple[bool, str]:
        """
        Verifica se o usuário pode criar mais empréstimos
        Retorna: (pode_criar, mensagem)
        """
        limites = await self.obter_limites_usuario(usuario_id)
        uso = await self.obter_uso_atual(usuario_id)
        
        # Verificar limite total
        if limites.max_emprestimos != -1 and uso["emprestimos"] >= limites.max_emprestimos:
            return False, f"Limite de {limites.max_emprestimos} empréstimos totais atingido. Faça upgrade do seu plano."
        
        # Verificar limite mensal
        if limites.max_emprestimos_mes != -1 and uso["emprestimos_mes"] >= limites.max_emprestimos_mes:
            return False, f"Limite de {limites.max_emprestimos_mes} empréstimos por mês atingido. Aguarde o próximo mês ou faça upgrade."
        
        return True, "OK"
    
    async def verificar_recurso(self, usuario_id: str, recurso: str) -> Tuple[bool, str]:
        """
        Verifica se o usuário tem acesso a um recurso específico
        Recursos: relatorios_avancados, contratos_personalizados, assistente_ia, api_acesso, multi_usuarios
        """
        limites = await self.obter_limites_usuario(usuario_id)
        
        recurso_map = {
            "relatorios_basicos": limites.relatorios_basicos,
            "relatorios_avancados": limites.relatorios_avancados,
            "contratos_pdf": limites.contratos_pdf,
            "contratos_personalizados": limites.contratos_personalizados,
            "assistente_ia": limites.assistente_ia,
            "api_acesso": limites.api_acesso,
            "multi_usuarios": limites.multi_usuarios,
            "notificacoes_email": limites.notificacoes_email,
            "notificacoes_whatsapp": limites.notificacoes_whatsapp,
            "suporte_prioritario": limites.suporte_prioritario,
            "suporte_24_7": limites.suporte_24_7
        }
        
        if recurso not in recurso_map:
            return False, f"Recurso '{recurso}' não reconhecido"
        
        if not recurso_map[recurso]:
            return False, f"O recurso '{recurso}' não está disponível no seu plano. Faça upgrade para ter acesso."
        
        return True, "OK"
    
    async def obter_resumo_uso(self, usuario_id: str) -> dict:
        """
        Retorna um resumo completo do uso e limites do usuário
        """
        limites = await self.obter_limites_usuario(usuario_id)
        uso = await self.obter_uso_atual(usuario_id)
        
        usuario = await self.db.usuarios.find_one({"id": usuario_id})
        plano = usuario.get("plano", "trial") if usuario else "trial"
        
        # Buscar info do plano
        plano_db = await self.db.planos.find_one({"slug": plano})
        
        return {
            "plano": plano,
            "plano_nome": plano_db.get("nome", plano.title()) if plano_db else plano.title(),
            "uso": {
                "clientes": {
                    "atual": uso["clientes"],
                    "limite": limites.max_clientes,
                    "ilimitado": limites.max_clientes == -1,
                    "percentual": (uso["clientes"] / limites.max_clientes * 100) if limites.max_clientes > 0 else 0
                },
                "emprestimos": {
                    "atual": uso["emprestimos"],
                    "limite": limites.max_emprestimos,
                    "ilimitado": limites.max_emprestimos == -1,
                    "percentual": (uso["emprestimos"] / limites.max_emprestimos * 100) if limites.max_emprestimos > 0 else 0
                },
                "emprestimos_mes": {
                    "atual": uso["emprestimos_mes"],
                    "limite": limites.max_emprestimos_mes,
                    "ilimitado": limites.max_emprestimos_mes == -1,
                    "percentual": (uso["emprestimos_mes"] / limites.max_emprestimos_mes * 100) if limites.max_emprestimos_mes > 0 else 0
                }
            },
            "recursos": {
                "relatorios_basicos": limites.relatorios_basicos,
                "relatorios_avancados": limites.relatorios_avancados,
                "contratos_pdf": limites.contratos_pdf,
                "contratos_personalizados": limites.contratos_personalizados,
                "assistente_ia": limites.assistente_ia,
                "api_acesso": limites.api_acesso,
                "multi_usuarios": limites.multi_usuarios,
                "notificacoes_email": limites.notificacoes_email,
                "notificacoes_whatsapp": limites.notificacoes_whatsapp,
                "suporte_prioritario": limites.suporte_prioritario,
                "suporte_24_7": limites.suporte_24_7
            }
        }

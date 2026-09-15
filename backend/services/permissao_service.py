"""
Serviço de Permissões e Limites
Todas as validações de plano e limites são feitas aqui no backend.
Admin/operador da plataforma tem acesso total sem restrições.
"""
from datetime import datetime, timezone
from typing import Tuple, Optional, List
from fastapi import HTTPException, Depends
from motor.motor_asyncio import AsyncIOMotorDatabase

from config import db
from models.usuario import Usuario
from models.plano import get_plano_limites, PlanoLimites, PLANOS_PADRAO
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_owner, is_operador_plataforma, PERFIL_OPERADOR
from services.permissoes_equipe import PERMISSOES_VALIDAS, ROTULOS as ROTULOS_PERMISSAO


class PermissaoService:
    """Serviço central de verificação de permissões e limites"""
    
    # Recursos disponíveis no sistema
    RECURSOS = [
        'relatorios_basicos',
        'relatorios_avancados', 
        'contratos_pdf',
        'contratos_personalizados',
        'assistente_ia',
        'api_acesso',
        'multi_usuarios',
        'notificacoes_email',
        'notificacoes_whatsapp',
        'suporte_prioritario',
        'suporte_24_7',
        'exportacao_dados',
        'simulacao'
    ]
    
    # Nomes amigáveis dos recursos para mensagens
    RECURSOS_NOMES = {
        'relatorios_basicos': 'Relatórios Básicos',
        'relatorios_avancados': 'Relatórios Avançados',
        'contratos_pdf': 'Contratos em PDF',
        'contratos_personalizados': 'Contratos Personalizados',
        'assistente_ia': 'Assistente com IA',
        'api_acesso': 'Acesso à API',
        'multi_usuarios': 'Multi-Usuários',
        'notificacoes_email': 'Notificações por Email',
        'notificacoes_whatsapp': 'Notificações por WhatsApp',
        'suporte_prioritario': 'Suporte Prioritário',
        'suporte_24_7': 'Suporte 24/7',
        'exportacao_dados': 'Exportação de Dados',
        'simulacao': 'Simulação de Empréstimos'
    }
    
    def __init__(self, database: AsyncIOMotorDatabase = None):
        self.db = database or db
    
    def is_admin(self, usuario: Usuario) -> bool:
        """Operador da plataforma (acesso total / cross-tenant)."""
        return is_operador_plataforma(usuario)

    def tem_acesso_ilimitado(self, usuario: Usuario) -> bool:
        """Bypass de limites de plano: operador da plataforma OU plano_ilimitado.
        plano_ilimitado NÃO concede acesso ao painel da plataforma."""
        return self.is_admin(usuario) or bool(getattr(usuario, "plano_ilimitado", False))
    
    async def obter_limites(self, usuario: Usuario) -> PlanoLimites:
        """
        Obtém os limites do plano do usuário (ou do dono).
        Admin retorna limites ilimitados.
        """
        # Se for funcionário, obter limites do DONO
        if usuario.owner_id:
            dono = await self.db.usuarios.find_one({"id": usuario.owner_id})
            if not dono:
                # Fallback se dono não encontrado
                return get_plano_limites("trial")
            # Converter dict p/ objeto Usuario se necessário, ou usar dict direto
            # Aqui vamos assumir que o campo 'plano' está no dict
            plano_slug = dono.get("plano", "trial")
            
            # Se dono for admin, limites infinitos
            if dono.get("perfil") == PERFIL_OPERADOR or dono.get("plano_ilimitado", False):
                 return PlanoLimites(
                    max_clientes=-1, max_emprestimos=-1, max_emprestimos_mes=-1,
                    relatorios_basicos=True, relatorios_avancados=True, contratos_pdf=True,
                    contratos_personalizados=True, assistente_ia=True, api_acesso=True,
                    multi_usuarios=True, notificacoes_email=True, notificacoes_whatsapp=True,
                    suporte_email=True, suporte_prioritario=True, suporte_24_7=True,
                    exportacao_dados=True, simulacao=True
                )
        else:
            plano_slug = usuario.plano

        # Admin tem tudo ilimitado
        if self.tem_acesso_ilimitado(usuario):
            return PlanoLimites(
                max_clientes=-1,
                max_emprestimos=-1,
                max_emprestimos_mes=-1,
                relatorios_basicos=True,
                relatorios_avancados=True,
                contratos_pdf=True,
                contratos_personalizados=True,
                assistente_ia=True,
                api_acesso=True,
                multi_usuarios=True,
                notificacoes_email=True,
                notificacoes_whatsapp=True,
                suporte_email=True,
                suporte_prioritario=True,
                suporte_24_7=True,
                exportacao_dados=True,
                simulacao=True
            )
        
        # Buscar plano customizado do banco primeiro
        plano_db = await self.db.planos.find_one({"slug": plano_slug})
        if plano_db and plano_db.get("limites"):
            return PlanoLimites(**plano_db["limites"])
        
        # Usar limites padrão
        return get_plano_limites(plano_slug)
    
    async def verificar_plano_ativo(self, usuario: Usuario) -> Tuple[bool, str]:
        """
        Verifica se o plano do usuário (ou dono) está ativo.
        """
        if self.tem_acesso_ilimitado(usuario):
            return True, "OK"
            
        target_user = usuario
        # Se for funcionário, verificar o dono
        if usuario.owner_id:
            dono_dict = await self.db.usuarios.find_one({"id": usuario.owner_id})
            if not dono_dict:
                return False, "Conta do proprietário não encontrada."
            # Criar objeto Usuario temporário para checagem ou checar dict
            # Convertendo string datas para datetime se necessário para comparação
            # Simplificação: Apenas verificamos campos booleanos e datas básicas
            
            plano_ativo = dono_dict.get("plano_ativo", False)
            if not plano_ativo:
                 return False, "O plano da conta principal está inativo."
            
            # TODO: Verificar datas de expiração do dono também se necessário
            # Por enquanto, assumimos que 'plano_ativo' no banco já reflete o status real (jobs que atualizam)
            return True, "OK"
        
        # Verificar se está ativo
        if not usuario.plano_ativo:
            return False, "Seu plano está inativo. Por favor, renove sua assinatura."
        
        # Verificar trial expirado (apenas se for o próprio dono/usuario e estiver em trial)
        if usuario.plano == 'trial' and usuario.data_fim_trial:
            if datetime.now(timezone.utc) > usuario.data_fim_trial:
                return False, "Seu período de teste expirou. Assine um plano para continuar usando o sistema."
        
        # Verificar assinatura expirada
        if usuario.data_vencimento_assinatura:
            if datetime.now(timezone.utc) > usuario.data_vencimento_assinatura:
                return False, "Sua assinatura expirou. Por favor, renove para continuar usando o sistema."
        
        return True, "OK"
    
    async def verificar_limite_clientes(self, usuario: Usuario) -> Tuple[bool, str, dict]:
        """
        Verifica se o usuário pode adicionar mais clientes.
        Verifica no contexto do DONO.
        """
        if self.tem_acesso_ilimitado(usuario):
            return True, "OK", {"limite": -1, "atual": 0, "ilimitado": True}
        
        # 1. Obter limites (já resolve owner)
        limites = await self.obter_limites(usuario)
        
        # 2. Definir contexto (quem paga a conta)
        context_id = get_user_context(usuario)
        
        # 3. Contar clientes do contexto
        total_clientes = await self.db.clientes.count_documents({"usuario_id": context_id})
        
        info = {
            "limite": limites.max_clientes,
            "atual": total_clientes,
            "ilimitado": limites.max_clientes == -1
        }
        
        # -1 significa ilimitado
        if limites.max_clientes == -1:
            return True, "OK", info
        
        if total_clientes >= limites.max_clientes:
            return False, f"Limite de {limites.max_clientes} clientes atingido na conta principal.", info
        
        return True, "OK", info
    
    async def verificar_limite_emprestimos(self, usuario: Usuario) -> Tuple[bool, str, dict]:
        """
        Verifica se o usuário pode criar mais empréstimos.
        Verifica limites no contexto do DONO.
        """
        if self.tem_acesso_ilimitado(usuario):
            return True, "OK", {"limite_total": -1, "limite_mes": -1, "atual": 0, "atual_mes": 0, "ilimitado": True}
        
        limites = await self.obter_limites(usuario)
        context_id = get_user_context(usuario)
        
        # Contar empréstimos totais do contexto
        total_emprestimos = await self.db.emprestimos.count_documents({"usuario_id": context_id})
        
        # Contar empréstimos do mês atual do contexto
        inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        emprestimos_mes = await self.db.emprestimos.count_documents({
            "usuario_id": context_id,
            "created_at": {"$gte": inicio_mes.isoformat()}
        })
        
        info = {
            "limite_total": limites.max_emprestimos,
            "limite_mes": limites.max_emprestimos_mes,
            "atual": total_emprestimos,
            "atual_mes": emprestimos_mes,
            "ilimitado": limites.max_emprestimos == -1
        }
        
        # Verificar limite total
        if limites.max_emprestimos != -1 and total_emprestimos >= limites.max_emprestimos:
            return False, f"Limite de {limites.max_emprestimos} empréstimos totais atingido na conta principal.", info
        
        # Verificar limite mensal
        if limites.max_emprestimos_mes != -1 and emprestimos_mes >= limites.max_emprestimos_mes:
            return False, f"Limite de {limites.max_emprestimos_mes} empréstimos por mês atingido na conta principal.", info
        
        return True, "OK", info
    
    async def verificar_recurso(self, usuario: Usuario, recurso: str) -> Tuple[bool, str]:
        """
        Verifica se o usuário tem acesso a um recurso específico.
        Admin tem acesso a todos os recursos.
        """
        if self.tem_acesso_ilimitado(usuario):
            return True, "OK"
        
        if recurso not in self.RECURSOS:
            return False, f"Recurso '{recurso}' não reconhecido"
        
        limites = await self.obter_limites(usuario)
        
        # Mapear recurso para atributo do PlanoLimites
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
            "suporte_24_7": limites.suporte_24_7,
            "exportacao_dados": limites.exportacao_dados,
            "simulacao": limites.simulacao
        }
        
        if not recurso_map.get(recurso, False):
            nome_recurso = self.RECURSOS_NOMES.get(recurso, recurso.replace('_', ' ').title())
            return False, f"O recurso '{nome_recurso}' não está disponível no seu plano. Faça upgrade para ter acesso."
        
        return True, "OK"
    
    async def obter_resumo_permissoes(self, usuario: Usuario) -> dict:
        """Retorna resumo completo das permissões e uso do usuário"""
        is_admin = self.tem_acesso_ilimitado(usuario)
        limites = await self.obter_limites(usuario)
        
        # Contadores de uso (não precisa contar para admin, mas vamos contar mesmo assim)
        total_clientes = await self.db.clientes.count_documents({"usuario_id": usuario.id})
        total_emprestimos = await self.db.emprestimos.count_documents({"usuario_id": usuario.id})
        
        inicio_mes = datetime.now(timezone.utc).replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        emprestimos_mes = await self.db.emprestimos.count_documents({
            "usuario_id": usuario.id,
            "created_at": {"$gte": inicio_mes.isoformat()}
        })
        
        # Verificar status do plano
        plano_ativo, plano_msg = await self.verificar_plano_ativo(usuario)
        
        # Calcular dias restantes do trial
        dias_trial = 0
        if usuario.plano == 'trial' and not is_admin and usuario.data_fim_trial:
            delta = usuario.data_fim_trial - datetime.now(timezone.utc)
            dias_trial = max(0, delta.days)
        
        return {
            "is_admin": is_admin,
            "perfil": usuario.perfil,
            "plano": {
                "slug": usuario.plano if not is_admin else "admin",
                "nome": "Administrador" if is_admin else PLANOS_PADRAO.get(usuario.plano, {}).get("nome", usuario.plano.title()),
                "ativo": plano_ativo,
                "mensagem": plano_msg if not plano_ativo else None,
                "dias_trial_restantes": dias_trial
            },
            "uso": {
                "clientes": {
                    "atual": total_clientes,
                    "limite": -1 if is_admin else limites.max_clientes,
                    "ilimitado": is_admin or limites.max_clientes == -1,
                    "percentual": 0 if (is_admin or limites.max_clientes == -1) else min(100, int(total_clientes / limites.max_clientes * 100))
                },
                "emprestimos": {
                    "atual": total_emprestimos,
                    "limite": -1 if is_admin else limites.max_emprestimos,
                    "ilimitado": is_admin or limites.max_emprestimos == -1,
                    "percentual": 0 if (is_admin or limites.max_emprestimos == -1) else min(100, int(total_emprestimos / limites.max_emprestimos * 100))
                },
                "emprestimos_mes": {
                    "atual": emprestimos_mes,
                    "limite": -1 if is_admin else limites.max_emprestimos_mes,
                    "ilimitado": is_admin or limites.max_emprestimos_mes == -1
                }
            },
            "recursos": {
                "relatorios_basicos": is_admin or limites.relatorios_basicos,
                "relatorios_avancados": is_admin or limites.relatorios_avancados,
                "contratos_pdf": is_admin or limites.contratos_pdf,
                "contratos_personalizados": is_admin or limites.contratos_personalizados,
                "assistente_ia": is_admin or limites.assistente_ia,
                "api_acesso": is_admin or limites.api_acesso,
                "multi_usuarios": is_admin or limites.multi_usuarios,
                "notificacoes_email": is_admin or limites.notificacoes_email,
                "notificacoes_whatsapp": is_admin or limites.notificacoes_whatsapp,
                "suporte_prioritario": is_admin or limites.suporte_prioritario,
                "suporte_24_7": is_admin or limites.suporte_24_7
            },
            # Vínculo de equipe. O membro não alcança GET /equipe (é do dono), então este é o
            # único lugar em que ele descobre o próprio cargo e o que foi liberado para ele.
            # Os rótulos saem do servidor, e não de uma lista na tela, para não divergirem de
            # services/permissoes_equipe.py — que é quem de fato concede ou nega o acesso.
            "equipe": {
                "e_membro": bool(usuario.owner_id),
                "cargo": usuario.cargo,
                "permissoes": [
                    {"id": p, "label": ROTULOS_PERMISSAO.get(p, p)}
                    for p in (usuario.permissoes or [])
                    if p in PERMISSOES_VALIDAS
                ],
            }
        }


# ==================== DEPENDENCIES PARA USAR NAS ROTAS ====================

# Instância global do serviço
permissao_service = PermissaoService()


async def verificar_plano_ativo(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Dependency que verifica se o plano está ativo.
    Usar em rotas que requerem plano ativo.
    """
    ativo, mensagem = await permissao_service.verificar_plano_ativo(current_user)
    if not ativo:
        raise HTTPException(status_code=403, detail=mensagem)
    return current_user


async def verificar_pode_criar_cliente(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Dependency que verifica se pode criar cliente.
    Usar na rota de criar cliente.
    """
    # Primeiro verifica plano ativo
    ativo, msg_plano = await permissao_service.verificar_plano_ativo(current_user)
    if not ativo:
        raise HTTPException(status_code=403, detail=msg_plano)
    
    # Depois verifica limite
    pode, mensagem, _ = await permissao_service.verificar_limite_clientes(current_user)
    if not pode:
        raise HTTPException(status_code=403, detail=mensagem)
    
    return current_user


async def verificar_pode_criar_emprestimo(current_user: Usuario = Depends(get_current_user)) -> Usuario:
    """
    Dependency que verifica se pode criar empréstimo.
    Usar na rota de criar empréstimo.
    """
    # Primeiro verifica plano ativo
    ativo, msg_plano = await permissao_service.verificar_plano_ativo(current_user)
    if not ativo:
        raise HTTPException(status_code=403, detail=msg_plano)
    
    # Depois verifica limite
    pode, mensagem, _ = await permissao_service.verificar_limite_emprestimos(current_user)
    if not pode:
        raise HTTPException(status_code=403, detail=mensagem)
    
    return current_user


def verificar_recurso(recurso: str):
    """
    Factory de dependency que verifica acesso a um recurso específico.
    Uso: Depends(verificar_recurso("assistente_ia"))
    """
    async def _verificar(current_user: Usuario = Depends(get_current_user)) -> Usuario:
        pode, mensagem = await permissao_service.verificar_recurso(current_user, recurso)
        if not pode:
            raise HTTPException(status_code=403, detail=mensagem)
        return current_user
    return _verificar

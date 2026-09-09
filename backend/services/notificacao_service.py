"""
Serviço de Notificações - Sistema Kredor
Gerencia criação e envio de notificações para usuários e admins
"""
from datetime import datetime, timezone, timedelta
from config import db
from utils.dinheiro import formatar_reais
import uuid
from typing import Optional, List
from services.whatsapp_service import enviar_notificacao_para_cliente, formatar_template_mensagem


async def criar_notificacao(
    usuario_id: str, 
    tipo: str, 
    titulo: str, 
    mensagem: str, 
    link: str = None,
    prioridade: str = "normal",
    dados_referencia: dict = None,
    emprestimo_id: str = None,
    cliente_id: str = None
):
    """
    Cria uma notificação para o usuário
    
    Args:
        usuario_id: ID do usuário que receberá a notificação
        tipo: Tipo da notificação (vencimento, atraso, suporte_novo, etc)
        titulo: Título da notificação
        mensagem: Mensagem da notificação
        link: Link opcional para onde a notificação deve redirecionar
        prioridade: baixa, normal, alta, urgente
        dados_referencia: Dados adicionais de referência
        emprestimo_id: ID do empréstimo relacionado (opcional)
        cliente_id: ID do cliente relacionado (opcional)
    """
    
    notificacao = {
        "id": str(uuid.uuid4()),
        "usuario_id": usuario_id,
        "tipo": tipo,
        "titulo": titulo,
        "mensagem": mensagem,
        "link": link,
        "lida": False,
        "prioridade": prioridade,
        "dados_referencia": dados_referencia,
        "emprestimo_id": emprestimo_id,
        "cliente_id": cliente_id,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    await db.notificacoes.insert_one(notificacao)
    return notificacao


async def criar_notificacao_para_admins(
    tipo: str,
    titulo: str,
    mensagem: str,
    link: str = None,
    prioridade: str = "normal",
    dados_referencia: dict = None
):
    """
    Cria uma notificação para todos os administradores
    """
    admins = await db.usuarios.find({"perfil": "admin"}).to_list(100)
    
    notificacoes_criadas = []
    for admin in admins:
        # Usar campo 'id' que é o UUID, não o _id do MongoDB
        admin_id = admin.get("id") or str(admin.get("_id"))
        
        notif = await criar_notificacao(
            usuario_id=admin_id,
            tipo=tipo,
            titulo=titulo,
            mensagem=mensagem,
            link=link,
            prioridade=prioridade,
            dados_referencia=dados_referencia
        )
        notificacoes_criadas.append(notif)
    
    return notificacoes_criadas


async def verificar_vencimentos_usuario(usuario_id: str) -> dict:
    """
    Verifica parcelas próximas do vencimento e em atraso para um usuário
    Cria notificações se necessário
    
    NOVA VERSÃO: Usa configurações personalizadas e envia WhatsApp
    """
    from services.notificacao_service_v2 import verificar_vencimentos_usuario_v2
    return await verificar_vencimentos_usuario_v2(usuario_id)


async def verificar_assinaturas_expirando() -> dict:
    """
    Verifica assinaturas/trials próximos de expirar e cria notificações
    """
    hoje = datetime.now(timezone.utc)
    proximos_3_dias = hoje + timedelta(days=3)
    proximos_7_dias = hoje + timedelta(days=7)
    
    notificacoes_criadas = 0
    
    # Buscar usuários com plano ativo
    usuarios = await db.usuarios.find({
        "plano_ativo": True
    }).to_list(1000)
    
    for usuario in usuarios:
        usuario_id = usuario.get("id")
        plano = usuario.get("plano", "trial")
        email = usuario.get("email", "")
        
        # Determinar data de expiração
        if plano == "trial":
            data_exp_str = usuario.get("data_fim_trial")
            tipo_notif = "trial_expirando"
        else:
            data_exp_str = usuario.get("data_expiracao_plano") or usuario.get("data_fim_trial")
            tipo_notif = "assinatura_expirando"
        
        if not data_exp_str:
            continue
        
        try:
            data_exp = datetime.fromisoformat(str(data_exp_str).replace('Z', '+00:00'))
            if data_exp.tzinfo is None:
                data_exp = data_exp.replace(tzinfo=timezone.utc)
            
            dias_restantes = (data_exp - hoje).days
            
            # Notificar se expira em 3 ou 7 dias
            if 0 < dias_restantes <= 7:
                # Verificar se já notificou hoje
                existente = await db.notificacoes.find_one({
                    "usuario_id": usuario_id,
                    "tipo": tipo_notif,
                    "created_at": {"$gte": (hoje - timedelta(hours=24)).isoformat()},
                    "deleted": {"$ne": True}
                })
                
                if not existente:
                    prioridade = "alta" if dias_restantes <= 3 else "normal"
                    
                    if plano == "trial":
                        titulo = f"⏰ Seu trial expira em {dias_restantes} dias!"
                        mensagem = "Aproveite e assine um plano para continuar usando todas as funcionalidades."
                    else:
                        titulo = f"⏰ Sua assinatura expira em {dias_restantes} dias!"
                        mensagem = "Renove sua assinatura para continuar usando o sistema."
                    
                    await criar_notificacao(
                        usuario_id=usuario_id,
                        tipo=tipo_notif,
                        titulo=titulo,
                        mensagem=mensagem,
                        link="/assinatura",
                        prioridade=prioridade,
                        dados_referencia={"dias_restantes": dias_restantes, "plano": plano}
                    )
                    notificacoes_criadas += 1
                    
        except (ValueError, TypeError) as e:
            print(f"Erro ao processar assinatura de {email}: {e}")
            continue
    
    return {"notificacoes_criadas": notificacoes_criadas}


async def criar_resumo_diario_admin() -> dict:
    """
    Cria um resumo diário para os administradores
    """
    hoje = datetime.now(timezone.utc)
    inicio_dia = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    
    # Contar métricas do dia
    novos_usuarios = await db.usuarios.count_documents({
        "created_at": {"$gte": inicio_dia.isoformat()}
    })
    
    novos_clientes = await db.clientes.count_documents({
        "created_at": {"$gte": inicio_dia.isoformat()}
    })
    
    pagamentos_hoje = await db.pagamentos.count_documents({
        "created_at": {"$gte": inicio_dia.isoformat()}
    })
    
    # Valor total de pagamentos
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio_dia.isoformat()}}},
        {"$group": {"_id": None, "total": {"$sum": "$valor_pago_centavos"}}}
    ]
    resultado = await db.pagamentos.aggregate(pipeline).to_list(1)
    valor_pagamentos = resultado[0]["total"] if resultado else 0
    
    # Parcelas em atraso (global)
    parcelas_atraso = await db.parcelas.count_documents({
        "status": {"$in": ["pendente", "parcial"]},
        "data_vencimento": {"$lt": hoje.isoformat()}
    })
    
    # Criar notificação para admins
    titulo = f"📊 Resumo do Dia - {hoje.strftime('%d/%m/%Y')}"
    mensagem = f"Novos usuários: {novos_usuarios} | Novos clientes: {novos_clientes} | Pagamentos: {pagamentos_hoje} (R$ {formatar_reais(valor_pagamentos)}) | Parcelas em atraso: {parcelas_atraso}"
    
    await criar_notificacao_para_admins(
        tipo="admin_resumo_diario",
        titulo=titulo,
        mensagem=mensagem,
        link="/admin/dashboard",
        prioridade="normal",
        dados_referencia={
            "novos_usuarios": novos_usuarios,
            "novos_clientes": novos_clientes,
            "pagamentos_hoje": pagamentos_hoje,
            "valor_pagamentos": valor_pagamentos,
            "parcelas_atraso": parcelas_atraso,
            "data": hoje.isoformat()
        }
    )
    
    return {
        "novos_usuarios": novos_usuarios,
        "novos_clientes": novos_clientes,
        "pagamentos_hoje": pagamentos_hoje,
        "valor_pagamentos": valor_pagamentos,
        "parcelas_atraso": parcelas_atraso
    }


async def notificar_novo_usuario(usuario_id: str, nome: str, email: str):
    """
    Cria notificação de boas-vindas para novo usuário e alerta para admins
    """
    # Notificação de boas-vindas para o usuário
    await criar_notificacao(
        usuario_id=usuario_id,
        tipo="boas_vindas",
        titulo="🎉 Bem-vindo ao Kredor!",
        mensagem="Seu cadastro foi realizado com sucesso. Comece explorando o sistema e cadastre seu primeiro cliente!",
        link="/onboarding",
        prioridade="normal"
    )
    
    # Notificação para admins
    await criar_notificacao_para_admins(
        tipo="admin_novo_usuario",
        titulo="👤 Novo usuário cadastrado",
        mensagem=f"{nome} ({email}) se cadastrou no sistema.",
        link="/superadmin/usuarios",
        prioridade="baixa",
        dados_referencia={"usuario_id": usuario_id, "nome": nome, "email": email}
    )


async def notificar_novo_cliente(usuario_id: str, cliente_nome: str, cliente_id: str):
    """
    Cria notificação quando um novo cliente é cadastrado
    """
    await criar_notificacao(
        usuario_id=usuario_id,
        tipo="sistema",
        titulo="✅ Cliente cadastrado com sucesso!",
        mensagem=f"O cliente {cliente_nome} foi cadastrado. Agora você pode criar empréstimos para ele.",
        link=f"/clientes/{cliente_id}",
        cliente_id=cliente_id,
        prioridade="baixa"
    )


async def notificar_pagamento_recebido(usuario_id: str, cliente_nome: str, valor: float, parcela_num: int, emprestimo_id: str):
    """
    Cria notificação quando um pagamento é registrado
    """
    await criar_notificacao(
        usuario_id=usuario_id,
        tipo="pagamento",
        titulo="💰 Pagamento Recebido!",
        mensagem=f"Pagamento de R$ {formatar_reais(valor)} recebido de {cliente_nome} (Parcela {parcela_num})",
        link=f"/emprestimos/{emprestimo_id}",
        emprestimo_id=emprestimo_id,
        prioridade="normal",
        dados_referencia={"valor": valor, "parcela": parcela_num, "cliente": cliente_nome}
    )

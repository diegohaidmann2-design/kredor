"""
Serviço de Notificações - Sistema Kredor
Gerencia criação e envio de notificações para usuários e admins
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.notificacao_service")

from datetime import datetime, timezone, timedelta
from config import db
from utils.dinheiro import formatar_reais
from models.notificacao import Notificacao
import uuid
from typing import Optional, List, Dict
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
    Verifica parcelas próximas do vencimento e em atraso para um usuário.
    Usa configurações personalizadas do usuário e envia via sistema/WhatsApp.
    """
    return await _verificar_vencimentos_usuario_impl(usuario_id)


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
            logger.error(f"Erro ao processar assinatura de {email}: {e}")
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


# ============================================================
# Verificação de vencimentos com configurações personalizadas
# (incorporado do antigo notificacao_service_v2)
# ============================================================

async def _registrar_controle_antispam(usuario_id: str, tipo: str, parcela_id: str, agora: datetime):
    """
    Registra marcador invisível (deleted=True) para deduplicação de 24h
    quando o canal 'sistema' está desativado. Sem isso, o WhatsApp seria
    reenviado ao cliente a cada execução horária do job (spam).
    """
    notif = Notificacao(
        usuario_id=usuario_id,
        tipo=tipo,
        titulo="[controle anti-spam]",
        mensagem="",
        lida=True,
        prioridade="baixa",
        dados_referencia={"parcela_id": parcela_id, "controle_antispam": True},
    )
    doc = notif.model_dump()
    doc["deleted"] = True  # marcador invisível de deduplicação; não faz parte do modelo
    doc["created_at"] = agora.isoformat()  # string ISO (convenção atual; conversão para Date é a tarefa 2.2)
    await db.notificacoes.insert_one(doc)


async def buscar_config_notificacoes(usuario_id: str) -> Dict:
    """
    Busca configurações de notificações do usuário.
    Retorna configuração padrão se não existir.
    """
    config = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": usuario_id
    })

    if not config or not config.get("dados"):
        return {
            "periodos": [
                {"dias": 3, "momento": "antes", "ativo": True},
                {"dias": 0, "momento": "no_dia", "ativo": True},
                {"dias": 3, "momento": "depois", "ativo": True}
            ],
            "canais": {
                "sistema": True,
                "whatsapp": False,
                "email": False
            },
            "template_whatsapp": "Olá {cliente_nome}! 👋\n\nParcela #{numero} de R$ {valor} vence em {dias} dias.\n\nData de vencimento: {data_vencimento}",
            "template_whatsapp_atraso": "Olá {cliente_nome}! ⚠️\n\nA parcela #{numero} de R$ {valor} está em atraso há {dias} dias.\n\nData de vencimento: {data_vencimento}\n\nPor favor, regularize sua situação.",
            "enviar_para_cliente": True,
            "ativo": True
        }

    return config.get("dados", {})


async def _verificar_vencimentos_usuario_impl(usuario_id: str) -> dict:
    """
    Verifica vencimentos usando configurações personalizadas do usuário
    e envia notificações via sistema e WhatsApp conforme configurado.
    """
    hoje = datetime.now(timezone.utc)

    config = await buscar_config_notificacoes(usuario_id)

    if not config.get("ativo", True):
        return {"notificacoes_criadas": 0, "mensagens_whatsapp": 0, "motivo": "notificacoes_desativadas"}

    emprestimos_ativos = await db.emprestimos.find({
        "usuario_id": usuario_id,
        "status": {"$ne": "quitado"},
        "deleted": {"$ne": True}
    }, {"id": 1}).to_list(10000)

    emprestimos_ativos_ids = [e["id"] for e in emprestimos_ativos]

    if not emprestimos_ativos_ids:
        return {"notificacoes_criadas": 0, "mensagens_whatsapp": 0, "motivo": "nenhum_emprestimo_ativo"}

    parcelas = await db.parcelas.find({
        "usuario_id": usuario_id,
        "emprestimo_id": {"$in": emprestimos_ativos_ids},
        "status": {"$in": ["pendente", "parcial", "atrasado"]},
        "deleted": {"$ne": True}
    }, {"_id": 0}).to_list(1000)

    notificacoes_criadas = 0
    mensagens_whatsapp_enviadas = 0
    erros_whatsapp = []

    for p in parcelas:
        try:
            if p.get("deleted"):
                continue

            data_venc_str = p.get("data_vencimento")
            if not data_venc_str:
                continue

            data_venc = datetime.fromisoformat(str(data_venc_str).replace('Z', '+00:00'))
            if data_venc.tzinfo is None:
                data_venc = data_venc.replace(tzinfo=timezone.utc)

            parcela_id = p.get("id")
            emprestimo_id = p.get("emprestimo_id")
            numero_parcela = p.get("numero_parcela", "?")
            valor_total_centavos = p.get("valor_total_centavos", 0)
            valor_pago_centavos = p.get("valor_pago_centavos", 0)
            valor_devido = valor_total_centavos - valor_pago_centavos

            emprestimo = await db.emprestimos.find_one({"id": emprestimo_id})
            if not emprestimo:
                continue

            if emprestimo.get("status") == "quitado" or emprestimo.get("deleted"):
                continue

            cliente_id = emprestimo.get("cliente_id")
            cliente = await db.clientes.find_one({"id": cliente_id})
            if not cliente:
                continue

            cliente_nome = cliente.get("nome", "Cliente")

            # Comparar apenas DATAS (sem hora) para classificar atraso vs vencimento.
            dias_diferenca = (data_venc.date() - hoje.date()).days

            if dias_diferenca < 0:
                dias_atraso = abs(dias_diferenca)

                deve_notificar = False
                for periodo in config.get("periodos", []):
                    if (periodo.get("momento") == "depois" and
                        periodo.get("ativo") and
                        periodo.get("dias") == dias_atraso):
                        deve_notificar = True
                        break

                if not deve_notificar:
                    continue

                existente = await db.notificacoes.find_one({
                    "usuario_id": usuario_id,
                    "tipo": "atraso",
                    "dados_referencia.parcela_id": parcela_id,
                    "created_at": {"$gte": (hoje - timedelta(hours=24)).isoformat()}
                })

                if existente:
                    continue

                if config.get("canais", {}).get("sistema", True):
                    await criar_notificacao(
                        usuario_id=usuario_id,
                        tipo="atraso",
                        titulo=f"⚠️ Parcela em Atraso - {dias_atraso} dias",
                        mensagem=f"{cliente_nome}: Parcela {numero_parcela} de R$ {formatar_reais(valor_devido)} está em atraso há {dias_atraso} dias",
                        link=f"/emprestimos/{emprestimo_id}",
                        prioridade="alta" if dias_atraso > 7 else "normal",
                        emprestimo_id=emprestimo_id,
                        cliente_id=cliente_id,
                        dados_referencia={
                            "parcela_id": parcela_id,
                            "dias_atraso": dias_atraso,
                            "valor": valor_devido,
                            "numero_parcela": numero_parcela
                        }
                    )
                    notificacoes_criadas += 1
                else:
                    await _registrar_controle_antispam(usuario_id, "atraso", parcela_id, hoje)

                if config.get("canais", {}).get("whatsapp") and config.get("enviar_para_cliente"):
                    template = config.get("template_whatsapp_atraso", "")
                    mensagem = formatar_template_mensagem(template, {
                        "cliente_nome": cliente_nome,
                        "numero": numero_parcela,
                        "valor": formatar_reais(valor_devido),
                        "dias": str(dias_atraso),
                        "data_vencimento": data_venc.strftime("%d/%m/%Y"),
                        "emprestimo_id": emprestimo_id
                    })

                    resultado = await enviar_notificacao_para_cliente(
                        usuario_id=usuario_id,
                        cliente_id=cliente_id,
                        mensagem=mensagem
                    )

                    if resultado.get("success"):
                        mensagens_whatsapp_enviadas += 1
                    else:
                        erros_whatsapp.append({
                            "cliente": cliente_nome,
                            "erro": resultado.get("message")
                        })

            else:
                dias_ate_vencimento = dias_diferenca

                deve_notificar = False
                momento_tipo = "no_dia" if dias_ate_vencimento == 0 else "antes"

                for periodo in config.get("periodos", []):
                    if (periodo.get("momento") == momento_tipo and
                        periodo.get("ativo") and
                        periodo.get("dias") == dias_ate_vencimento):
                        deve_notificar = True
                        break

                if not deve_notificar:
                    continue

                existente = await db.notificacoes.find_one({
                    "usuario_id": usuario_id,
                    "tipo": "vencimento",
                    "dados_referencia.parcela_id": parcela_id,
                    "created_at": {"$gte": (hoje - timedelta(hours=24)).isoformat()}
                })

                if existente:
                    continue

                if config.get("canais", {}).get("sistema", True):
                    if dias_ate_vencimento == 0:
                        titulo = "📅 Parcela Vence HOJE"
                        mensagem_texto = f"{cliente_nome}: Parcela {numero_parcela} de R$ {formatar_reais(valor_devido)} vence HOJE"
                    else:
                        titulo = f"📅 Parcela Vencendo em {dias_ate_vencimento} dias"
                        mensagem_texto = f"{cliente_nome}: Parcela {numero_parcela} de R$ {formatar_reais(valor_devido)} vence em {dias_ate_vencimento} dias"

                    await criar_notificacao(
                        usuario_id=usuario_id,
                        tipo="vencimento",
                        titulo=titulo,
                        mensagem=mensagem_texto,
                        link=f"/emprestimos/{emprestimo_id}",
                        prioridade="normal",
                        emprestimo_id=emprestimo_id,
                        cliente_id=cliente_id,
                        dados_referencia={
                            "parcela_id": parcela_id,
                            "dias_ate_vencimento": dias_ate_vencimento,
                            "valor": valor_devido,
                            "numero_parcela": numero_parcela
                        }
                    )
                    notificacoes_criadas += 1
                else:
                    await _registrar_controle_antispam(usuario_id, "vencimento", parcela_id, hoje)

                if config.get("canais", {}).get("whatsapp") and config.get("enviar_para_cliente"):
                    template = config.get("template_whatsapp", "")
                    dias_texto = "HOJE" if dias_ate_vencimento == 0 else str(dias_ate_vencimento)

                    mensagem = formatar_template_mensagem(template, {
                        "cliente_nome": cliente_nome,
                        "numero": numero_parcela,
                        "valor": formatar_reais(valor_devido),
                        "dias": dias_texto,
                        "data_vencimento": data_venc.strftime("%d/%m/%Y"),
                        "emprestimo_id": emprestimo_id
                    })

                    resultado = await enviar_notificacao_para_cliente(
                        usuario_id=usuario_id,
                        cliente_id=cliente_id,
                        mensagem=mensagem
                    )

                    if resultado.get("success"):
                        mensagens_whatsapp_enviadas += 1
                    else:
                        erros_whatsapp.append({
                            "cliente": cliente_nome,
                            "erro": resultado.get("message")
                        })

        except (ValueError, TypeError) as e:
            logger.error("Erro ao processar parcela em verificação de vencimentos",
                         data={"usuario_id": usuario_id, "parcela_id": p.get("id"), "erro": str(e)})
            continue

    return {
        "notificacoes_criadas": notificacoes_criadas,
        "mensagens_whatsapp": mensagens_whatsapp_enviadas,
        "erros_whatsapp": erros_whatsapp if erros_whatsapp else None
    }


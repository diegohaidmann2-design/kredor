"""
Serviço centralizado de gerenciamento de planos.
Este serviço garante que todas as atualizações de plano sejam consistentes
em todos os módulos do sistema.
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.plano_service")

from datetime import datetime, timedelta, timezone
from typing import Optional
from config import db


async def ativar_plano_pago(
    usuario_id: str,
    plano_id: str,
    payment_id: str,
    gateway: str = "asaas",
    dias_validade: int = 30,
    valor: float = 0,
    origem: str = "webhook"
) -> dict:
    """
    Ativa um plano pago para um usuário.
    
    Esta função centraliza toda a lógica de ativação de plano, garantindo:
    - Encerramento do período TRIAL
    - Atualização do plano para o plano pago
    - Definição correta da data de expiração
    - Sincronização em todos os módulos (usuarios, assinaturas, transacoes)
    - Registro de log de auditoria
    
    Args:
        usuario_id: ID do usuário
        plano_id: ID do plano (basico, profissional, enterprise)
        payment_id: ID do pagamento no gateway
        gateway: Gateway de pagamento (asaas, syncpay)
        dias_validade: Dias de validade do plano (padrão: 30)
        valor: Valor pago
        origem: Origem da ativação (webhook, manual, checkout)
    
    Returns:
        dict com status da operação
    """
    agora = datetime.now(timezone.utc)
    data_expiracao = agora + timedelta(days=dias_validade)
    
    # Buscar dados atuais do usuário para log
    usuario_atual = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
    
    if not usuario_atual:
        return {
            "success": False,
            "error": f"Usuário não encontrado: {usuario_id}"
        }
    
    plano_anterior = usuario_atual.get("plano", "trial")
    era_trial = plano_anterior == "trial"
    
    # 1. Atualizar usuário - CAMPOS CRÍTICOS
    update_usuario = {
        # Dados do plano
        "plano": plano_id,
        "plano_ativo": True,
        
        # Datas de expiração - usar campo unificado
        "data_expiracao_plano": data_expiracao.isoformat(),
        
        # Limpar dados de trial
        "data_fim_trial": None,  # Importante: limpar para não causar confusão
        
        # Dados do pagamento
        "gateway_pagamento": gateway,
        "payment_status": "approved",
        f"{gateway}_payment_id": payment_id,
        
        # Metadados
        "ultima_atualizacao_plano": agora.isoformat(),
        "updated_at": agora.isoformat()
    }
    
    result = await db.usuarios.update_one(
        {"id": usuario_id},
        {"$set": update_usuario}
    )
    
    if result.modified_count == 0:
        return {
            "success": False,
            "error": "Falha ao atualizar usuário"
        }
    
    # 2. Atualizar transação de checkout (se existir)
    await db.transacoes_checkout.update_one(
        {"payment_id": payment_id},
        {"$set": {
            "status": "approved",
            "atualizado_em": agora,
            "plano_ativado": True
        }}
    )
    
    # 3. Registrar assinatura ativa
    assinatura_id = f"{usuario_id}_{plano_id}_{int(agora.timestamp())}"
    
    await db.assinaturas.update_one(
        {"usuario_id": usuario_id, "status": "ativa"},
        {"$set": {"status": "substituida", "substituida_em": agora.isoformat()}},
    )
    
    await db.assinaturas.insert_one({
        "id": assinatura_id,
        "usuario_id": usuario_id,
        "plano_id": plano_id,
        "payment_id": payment_id,
        "gateway": gateway,
        "status": "ativa",
        "valor": valor,
        "data_inicio": agora.isoformat(),
        "data_expiracao": data_expiracao.isoformat(),
        "origem": origem,
        "created_at": agora.isoformat()
    })
    
    # 4. Registrar log de auditoria
    await db.logs_planos.insert_one({
        "usuario_id": usuario_id,
        "usuario_email": usuario_atual.get("email"),
        "acao": "ativacao_plano",
        "plano_anterior": plano_anterior,
        "plano_novo": plano_id,
        "era_trial": era_trial,
        "payment_id": payment_id,
        "gateway": gateway,
        "valor": valor,
        "data_expiracao": data_expiracao.isoformat(),
        "origem": origem,
        "data_acao": agora.isoformat()
    })
    
    logger.info(f"✅ [PlanoService] Plano ativado: {usuario_atual.get('email')}")
    logger.info(f"   Plano: {plano_anterior} → {plano_id}")
    logger.info(f"   Expira em: {data_expiracao.strftime('%d/%m/%Y')}")
    logger.info(f"   Payment ID: {payment_id}")
    
    return {
        "success": True,
        "usuario_id": usuario_id,
        "plano_anterior": plano_anterior,
        "plano_novo": plano_id,
        "data_expiracao": data_expiracao.isoformat(),
        "era_trial": era_trial
    }


async def obter_status_plano(usuario_id: str) -> dict:
    """
    Obtém o status atual do plano de um usuário de forma consistente.
    
    Returns:
        dict com informações unificadas do plano
    """
    usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
    
    if not usuario:
        return {
            "success": False,
            "error": "Usuário não encontrado"
        }
    
    plano = usuario.get("plano", "trial")
    plano_ativo = usuario.get("plano_ativo", False)
    
    # Determinar data de expiração correta
    if plano == "trial":
        data_expiracao = usuario.get("data_fim_trial")
        tipo = "trial"
    else:
        # Para planos pagos, usar data_expiracao_plano
        data_expiracao = usuario.get("data_expiracao_plano") or usuario.get("data_fim_trial")
        tipo = "pago"
    
    # Verificar se expirou
    expirado = False
    dias_restantes = None
    
    if data_expiracao:
        try:
            if isinstance(data_expiracao, str):
                data_exp = datetime.fromisoformat(data_expiracao.replace('Z', '+00:00'))
            else:
                data_exp = data_expiracao
            
            agora = datetime.now(timezone.utc)
            expirado = data_exp < agora
            dias_restantes = max(0, (data_exp - agora).days)
        except (ValueError, TypeError, AttributeError):
            pass
    
    return {
        "success": True,
        "plano": plano,
        "plano_nome": plano.capitalize() if plano else "Trial",
        "plano_ativo": plano_ativo and not expirado,
        "tipo": tipo,
        "data_expiracao": data_expiracao,
        "expirado": expirado,
        "dias_restantes": dias_restantes,
        "gateway": usuario.get("gateway_pagamento"),
        "payment_status": usuario.get("payment_status")
    }


async def verificar_e_corrigir_inconsistencias(usuario_id: str) -> dict:
    """
    Verifica e corrige inconsistências no plano de um usuário.
    
    Usado para reconciliação e correção de dados.
    """
    usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
    
    if not usuario:
        return {"success": False, "error": "Usuário não encontrado"}
    
    correcoes = []
    update_data = {}
    
    plano = usuario.get("plano", "trial")
    plano_ativo = usuario.get("plano_ativo", False)
    payment_status = usuario.get("payment_status")
    data_fim_trial = usuario.get("data_fim_trial")
    data_expiracao_plano = usuario.get("data_expiracao_plano")
    
    # Verificação 1: Plano pago com payment_status approved deve ter plano_ativo = True
    if plano != "trial" and payment_status == "approved" and not plano_ativo:
        update_data["plano_ativo"] = True
        correcoes.append("plano_ativo corrigido para True (pagamento aprovado)")
    
    # Verificação 2: Plano pago não deve ter data_fim_trial como referência principal
    if plano != "trial" and data_fim_trial and not data_expiracao_plano:
        # Migrar data_fim_trial para data_expiracao_plano
        update_data["data_expiracao_plano"] = data_fim_trial
        update_data["data_fim_trial"] = None
        correcoes.append("data_expiracao_plano definida a partir de data_fim_trial")
    
    # Verificação 3: Se é trial mas tem payment_status approved, pode ser inconsistência
    if plano == "trial" and payment_status == "approved":
        # Buscar última transação aprovada
        transacao = await db.transacoes_checkout.find_one(
            {"usuario_id": usuario_id, "status": "approved"},
            sort=[("atualizado_em", -1)]
        )
        if transacao and transacao.get("plano_id") != "trial":
            update_data["plano"] = transacao.get("plano_id")
            correcoes.append(f"plano corrigido de trial para {transacao.get('plano_id')}")
    
    if update_data:
        update_data["updated_at"] = datetime.now(timezone.utc).isoformat()
        await db.usuarios.update_one(
            {"id": usuario_id},
            {"$set": update_data}
        )
        
        # Log da correção
        await db.logs_planos.insert_one({
            "usuario_id": usuario_id,
            "usuario_email": usuario.get("email"),
            "acao": "correcao_inconsistencia",
            "correcoes": correcoes,
            "dados_anteriores": {
                "plano": plano,
                "plano_ativo": plano_ativo,
                "payment_status": payment_status
            },
            "dados_novos": update_data,
            "data_acao": datetime.now(timezone.utc).isoformat()
        })
    
    return {
        "success": True,
        "correcoes_aplicadas": len(correcoes),
        "correcoes": correcoes
    }


async def gerar_relatorio_reconciliacao() -> dict:
    """
    Gera relatório de reconciliação entre transações e status de assinatura.
    
    Identifica:
    - Transações aprovadas sem plano ativado
    - Planos ativos sem transação correspondente
    - Inconsistências de datas
    """
    relatorio = {
        "data_geracao": datetime.now(timezone.utc).isoformat(),
        "inconsistencias": [],
        "estatisticas": {}
    }
    
    # 1. Buscar transações aprovadas
    transacoes_aprovadas = await db.transacoes_checkout.find(
        {"status": "approved"}
    ).to_list(1000)
    
    relatorio["estatisticas"]["total_transacoes_aprovadas"] = len(transacoes_aprovadas)
    
    # 2. Verificar cada transação
    for transacao in transacoes_aprovadas:
        usuario_id = transacao.get("usuario_id")
        plano_transacao = transacao.get("plano_id")
        payment_id = transacao.get("payment_id")
        
        if not usuario_id:
            continue
        
        usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0})
        
        if not usuario:
            relatorio["inconsistencias"].append({
                "tipo": "usuario_nao_encontrado",
                "payment_id": payment_id,
                "usuario_id": usuario_id
            })
            continue
        
        # Verificar se plano está ativo
        if not usuario.get("plano_ativo"):
            relatorio["inconsistencias"].append({
                "tipo": "plano_nao_ativado",
                "usuario_id": usuario_id,
                "usuario_email": usuario.get("email"),
                "payment_id": payment_id,
                "plano_esperado": plano_transacao,
                "plano_atual": usuario.get("plano"),
                "plano_ativo": usuario.get("plano_ativo")
            })
        
        # Verificar se plano corresponde
        if usuario.get("plano") != plano_transacao:
            relatorio["inconsistencias"].append({
                "tipo": "plano_divergente",
                "usuario_id": usuario_id,
                "usuario_email": usuario.get("email"),
                "payment_id": payment_id,
                "plano_esperado": plano_transacao,
                "plano_atual": usuario.get("plano")
            })
    
    # 3. Buscar usuários com plano pago mas sem transação
    usuarios_pagos = await db.usuarios.find(
        {"plano": {"$ne": "trial"}, "plano_ativo": True}
    ).to_list(1000)
    
    relatorio["estatisticas"]["total_usuarios_pagos"] = len(usuarios_pagos)
    
    for usuario in usuarios_pagos:
        # Verificar se tem transação correspondente
        transacao = await db.transacoes_checkout.find_one({
            "usuario_id": usuario.get("id"),
            "status": "approved"
        })
        
        if not transacao:
            # Verificar em assinaturas_admin (criadas manualmente)
            assinatura_admin = await db.assinaturas_admin.find_one({
                "usuario_id": usuario.get("id"),
                "status": "ativa"
            })
            
            if not assinatura_admin:
                relatorio["inconsistencias"].append({
                    "tipo": "plano_sem_transacao",
                    "usuario_id": usuario.get("id"),
                    "usuario_email": usuario.get("email"),
                    "plano": usuario.get("plano"),
                    "observacao": "Plano ativo sem transação aprovada ou assinatura admin"
                })
    
    relatorio["estatisticas"]["total_inconsistencias"] = len(relatorio["inconsistencias"])
    
    return relatorio

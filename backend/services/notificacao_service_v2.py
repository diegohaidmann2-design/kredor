"""
Serviço de Notificações V2 - Com suporte a configurações personalizadas
Funções auxiliares para o sistema de notificações
"""
from datetime import datetime, timezone, timedelta
from config import db
from typing import Dict, List
from services.whatsapp_service import enviar_notificacao_para_cliente, formatar_template_mensagem


async def buscar_config_notificacoes(usuario_id: str) -> Dict:
    """
    Busca configurações de notificações do usuário
    Retorna configuração padrão se não existir
    """
    config = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": usuario_id
    })
    
    if not config or not config.get("dados"):
        # Configuração padrão
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


async def verificar_vencimentos_usuario_v2(usuario_id: str) -> dict:
    """
    Versão 2: Verifica vencimentos usando configurações personalizadas
    e envia notificações via sistema e WhatsApp conforme configurado
    """
    hoje = datetime.now(timezone.utc)
    
    # 1. Buscar configurações do usuário
    config = await buscar_config_notificacoes(usuario_id)
    
    # Se notificações desativadas, retornar
    if not config.get("ativo", True):
        return {"notificacoes_criadas": 0, "mensagens_whatsapp": 0, "motivo": "notificacoes_desativadas"}
    
    # 2. Buscar parcelas pendentes
    parcelas = await db.parcelas.find({
        "usuario_id": usuario_id,
        "status": {"$in": ["pendente", "parcial"]}
    }, {"_id": 0}).to_list(1000)
    
    notificacoes_criadas = 0
    mensagens_whatsapp_enviadas = 0
    erros_whatsapp = []
    
    # 3. Processar cada parcela
    for p in parcelas:
        try:
            data_venc_str = p.get("data_vencimento")
            if not data_venc_str:
                continue
                
            data_venc = datetime.fromisoformat(str(data_venc_str).replace('Z', '+00:00'))
            if data_venc.tzinfo is None:
                data_venc = data_venc.replace(tzinfo=timezone.utc)
            
            parcela_id = p.get("id")
            emprestimo_id = p.get("emprestimo_id")
            numero_parcela = p.get("numero_parcela", "?")
            valor_total = p.get("valor_total", 0)
            valor_pago = p.get("valor_pago", 0)
            valor_devido = valor_total - valor_pago
            
            # Buscar dados do empréstimo e cliente
            emprestimo = await db.emprestimos.find_one({"id": emprestimo_id})
            if not emprestimo:
                continue
                
            cliente_id = emprestimo.get("cliente_id")
            cliente = await db.clientes.find_one({"id": cliente_id})
            if not cliente:
                continue
                
            cliente_nome = cliente.get("nome", "Cliente")
            
            # 4. Determinar tipo de notificação (atraso ou vencimento)
            dias_diferenca = (data_venc - hoje).days
            
            if dias_diferenca < 0:
                # PARCELA EM ATRASO
                dias_atraso = abs(dias_diferenca)
                
                # Verificar se deve notificar este período
                deve_notificar = False
                for periodo in config.get("periodos", []):
                    if (periodo.get("momento") == "depois" and 
                        periodo.get("ativo") and 
                        periodo.get("dias") == dias_atraso):
                        deve_notificar = True
                        break
                
                if not deve_notificar:
                    continue
                
                # Verificar se já notificou nas últimas 24h (incluir deletadas para evitar duplicação)
                existente = await db.notificacoes.find_one({
                    "usuario_id": usuario_id,
                    "tipo": "atraso",
                    "dados_referencia.parcela_id": parcela_id,
                    "created_at": {"$gte": (hoje - timedelta(hours=24)).isoformat()}
                    # NÃO filtrar por deleted - queremos evitar duplicatas mesmo se usuário deletou
                })
                
                if existente:
                    continue
                
                # Criar notificação no sistema
                if config.get("canais", {}).get("sistema", True):
                    from services.notificacao_service import criar_notificacao
                    await criar_notificacao(
                        usuario_id=usuario_id,
                        tipo="atraso",
                        titulo=f"⚠️ Parcela em Atraso - {dias_atraso} dias",
                        mensagem=f"{cliente_nome}: Parcela {numero_parcela} de R$ {valor_devido:,.2f} está em atraso há {dias_atraso} dias",
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
                
                # Enviar via WhatsApp
                if config.get("canais", {}).get("whatsapp") and config.get("enviar_para_cliente"):
                    template = config.get("template_whatsapp_atraso", "")
                    mensagem = formatar_template_mensagem(template, {
                        "cliente_nome": cliente_nome,
                        "numero": numero_parcela,
                        "valor": f"{valor_devido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
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
                # PARCELA A VENCER
                dias_ate_vencimento = dias_diferenca
                
                # Verificar se deve notificar este período
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
                
                # Verificar se já notificou nas últimas 24h (incluir deletadas para evitar duplicação)
                existente = await db.notificacoes.find_one({
                    "usuario_id": usuario_id,
                    "tipo": "vencimento",
                    "dados_referencia.parcela_id": parcela_id,
                    "created_at": {"$gte": (hoje - timedelta(hours=24)).isoformat()}
                    # NÃO filtrar por deleted - queremos evitar duplicatas mesmo se usuário deletou
                })
                
                if existente:
                    continue
                
                # Criar notificação no sistema
                if config.get("canais", {}).get("sistema", True):
                    from services.notificacao_service import criar_notificacao
                    
                    if dias_ate_vencimento == 0:
                        titulo = f"📅 Parcela Vence HOJE"
                        mensagem_texto = f"{cliente_nome}: Parcela {numero_parcela} de R$ {valor_devido:,.2f} vence HOJE"
                    else:
                        titulo = f"📅 Parcela Vencendo em {dias_ate_vencimento} dias"
                        mensagem_texto = f"{cliente_nome}: Parcela {numero_parcela} de R$ {valor_devido:,.2f} vence em {dias_ate_vencimento} dias"
                    
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
                
                # Enviar via WhatsApp
                if config.get("canais", {}).get("whatsapp") and config.get("enviar_para_cliente"):
                    template = config.get("template_whatsapp", "")
                    
                    if dias_ate_vencimento == 0:
                        dias_texto = "HOJE"
                    else:
                        dias_texto = str(dias_ate_vencimento)
                    
                    mensagem = formatar_template_mensagem(template, {
                        "cliente_nome": cliente_nome,
                        "numero": numero_parcela,
                        "valor": f"{valor_devido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
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
            print(f"Erro ao processar parcela {parcela_id}: {e}")
            continue
    
    return {
        "notificacoes_criadas": notificacoes_criadas,
        "mensagens_whatsapp": mensagens_whatsapp_enviadas,
        "erros_whatsapp": erros_whatsapp if erros_whatsapp else None
    }

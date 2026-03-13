"""
Rotas WhatsApp - Gestão de conexões e envio de mensagens
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timedelta, timezone
import httpx
import uuid
import asyncio

from config import db
from models.whatsapp import (
    WhatsAppConexao, 
    WhatsAppMensagem, 
    EnviarMensagemRequest,
    EvolutionAPIConfig
)
from models.usuario import Usuario
from services.auth import get_current_user, require_admin

router = APIRouter()


# ============ LOGS E AUDITORIA ============

@router.get("/logs")
async def listar_logs_whatsapp(
    tipo: str = None,
    status: str = None,
    cliente_id: str = None,
    data_inicio: str = None,
    data_fim: str = None,
    limit: int = 100,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista logs de envios de WhatsApp do usuário
    
    Filtros:
    - tipo: cobranca_manual, confirmacao_pagamento, etc
    - status: enviado, erro, pendente
    - cliente_id: filtrar por cliente específico
    - data_inicio/data_fim: período
    """
    filtro = {"usuario_id": current_user.id}
    
    if tipo:
        filtro["tipo"] = tipo
    if status:
        filtro["status"] = status
    if cliente_id:
        filtro["cliente_id"] = cliente_id
    if data_inicio:
        filtro["created_at"] = {"$gte": data_inicio}
    if data_fim:
        if "created_at" in filtro:
            filtro["created_at"]["$lte"] = data_fim
        else:
            filtro["created_at"] = {"$lte": data_fim}
    
    logs = await db.whatsapp_mensagens_log.find(filtro) \
        .sort("created_at", -1) \
        .limit(limit) \
        .to_list(limit)
    
    # Enriquecer com dados do cliente e remover _id do MongoDB
    for log in logs:
        # Remover _id do MongoDB para evitar erro de serialização
        if "_id" in log:
            log.pop("_id")
        
        if log.get("cliente_id"):
            cliente = await db.clientes.find_one({"id": log["cliente_id"]}, {"nome": 1})
            log["cliente_nome"] = cliente.get("nome") if cliente else "Cliente não encontrado"
    
    return {
        "items": logs,
        "total": len(logs)
    }


@router.get("/logs/estatisticas")
async def estatisticas_logs_whatsapp(
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna estatísticas de envios WhatsApp do usuário"""
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = hoje - timedelta(days=7)
    inicio_mes = hoje - timedelta(days=30)
    
    # Total de envios
    total = await db.whatsapp_mensagens_log.count_documents({"usuario_id": current_user.id})
    
    # Envios hoje
    hoje_count = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": current_user.id,
        "created_at": {"$gte": hoje.isoformat()}
    })
    
    # Envios na semana
    semana_count = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": current_user.id,
        "created_at": {"$gte": inicio_semana.isoformat()}
    })
    
    # Envios no mês
    mes_count = await db.whatsapp_mensagens_log.count_documents({
        "usuario_id": current_user.id,
        "created_at": {"$gte": inicio_mes.isoformat()}
    })
    
    # Sucessos vs Erros (últimos 7 dias)
    pipeline_status = [
        {"$match": {
            "usuario_id": current_user.id,
            "created_at": {"$gte": inicio_semana.isoformat()}
        }},
        {"$group": {
            "_id": "$status",
            "count": {"$sum": 1}
        }}
    ]
    status_result = await db.whatsapp_mensagens_log.aggregate(pipeline_status).to_list(10)
    
    status_stats = {}
    for item in status_result:
        status_stats[item["_id"]] = item["count"]
    
    # Taxa de sucesso
    enviados = status_stats.get("enviado", 0)
    erros = status_stats.get("erro", 0)
    taxa_sucesso = (enviados / (enviados + erros) * 100) if (enviados + erros) > 0 else 0
    
    # Verificar status da conexão WhatsApp
    conexao = await db.whatsapp_conexoes.find_one({
        "usuario_id": current_user.id,
        "status": "conectado"
    })
    
    servico_ativo = conexao is not None
    
    return {
        "total_envios": total,
        "hoje": hoje_count,
        "ultimos_7_dias": semana_count,
        "ultimos_30_dias": mes_count,
        "status": {
            "enviados": enviados,
            "erros": erros,
            "pendentes": status_stats.get("pendente", 0)
        },
        "taxa_sucesso": round(taxa_sucesso, 2),
        "servico": {
            "ativo": servico_ativo,
            "status": "conectado" if servico_ativo else "desconectado",
            "mensagem": "WhatsApp conectado e funcionando" if servico_ativo else "WhatsApp não conectado"
        }
    }


@router.get("/status-servico")
async def verificar_status_servico(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Verifica status completo do serviço WhatsApp
    - Conexão ativa
    - Últimos envios
    - Taxa de sucesso
    - Problemas recentes
    """
    # Verificar conexão
    conexao = await db.whatsapp_conexoes.find_one({
        "usuario_id": current_user.id,
        "status": "conectado"
    })
    
    servico_ativo = conexao is not None
    
    # Verificar últimos 10 envios
    ultimos_envios = await db.whatsapp_mensagens_log.find({
        "usuario_id": current_user.id
    }).sort("created_at", -1).limit(10).to_list(10)
    
    # Calcular taxa de sucesso dos últimos envios
    if ultimos_envios:
        sucessos = sum(1 for e in ultimos_envios if e.get("status") == "enviado")
        taxa_sucesso_recente = (sucessos / len(ultimos_envios)) * 100
    else:
        taxa_sucesso_recente = 0
    
    # Identificar problemas
    problemas = []
    if not servico_ativo:
        problemas.append({
            "tipo": "conexao",
            "gravidade": "alta",
            "mensagem": "WhatsApp não está conectado. Conecte em Configurações > WhatsApp"
        })
    
    if taxa_sucesso_recente < 50 and len(ultimos_envios) >= 5:
        problemas.append({
            "tipo": "taxa_erro",
            "gravidade": "media",
            "mensagem": f"Taxa de sucesso baixa ({taxa_sucesso_recente:.0f}%). Verifique a conexão."
        })
    
    # Verificar se há muitos erros recentes
    erros_recentes = sum(1 for e in ultimos_envios if e.get("status") == "erro")
    if erros_recentes >= 3:
        problemas.append({
            "tipo": "erros_consecutivos",
            "gravidade": "alta",
            "mensagem": f"{erros_recentes} erros nos últimos envios. Reconecte o WhatsApp."
        })
    
    return {
        "servico_ativo": servico_ativo,
        "status_geral": "funcionando" if servico_ativo and len(problemas) == 0 else "com_problemas" if servico_ativo else "inativo",
        "conexao": {
            "ativa": servico_ativo,
            "numero_telefone": conexao.get("numero_telefone") if conexao else None,
            "data_conexao": conexao.get("data_conexao") if conexao else None
        },
        "ultimos_envios": {
            "total": len(ultimos_envios),
            "taxa_sucesso": round(taxa_sucesso_recente, 2)
        },
        "problemas": problemas,
        "recomendacoes": [
            "Mantenha o WhatsApp conectado sempre" if not servico_ativo else None,
            "Evite enviar muitas mensagens em curto período",
            "Use o modo fila para envios automáticos"
        ]
    }


# ============ CONFIGURAÇÕES (SUPER ADMIN) ============

@router.get("/config/evolution")
async def obter_config_evolution(
    current_user: Usuario = Depends(require_admin)
):
    """Obtém configuração da Evolution API (Super Admin)"""
    config = await db.configuracoes.find_one(
        {"tipo": "evolution_api"}, 
        {"_id": 0}
    )
    
    if not config:
        return EvolutionAPIConfig().model_dump()
    
    return config.get("dados", EvolutionAPIConfig().model_dump())


@router.put("/config/evolution")
async def atualizar_config_evolution(
    config: EvolutionAPIConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Atualiza configuração da Evolution API (Super Admin)"""
    await db.configuracoes.update_one(
        {"tipo": "evolution_api"},
        {"$set": {
            "tipo": "evolution_api", 
            "dados": config.model_dump(),
            "updated_at": datetime.now(timezone.utc).isoformat()
        }},
        upsert=True
    )
    
    return {"message": "Configurações Evolution API atualizadas"}



@router.post("/config/evolution/test")
async def testar_config_evolution(
    config: EvolutionAPIConfig,
    current_user: Usuario = Depends(require_admin)
):
    """Testa conexão com Evolution API (Super Admin)"""
    if not config.habilitado or not config.api_url or not config.api_key:
        raise HTTPException(400, "Configure a URL da API e a API Key antes de testar")
    
    # Fazer requisição de teste para a Evolution API
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            response = await client.get(
                f"{config.api_url}/instance/fetchInstances",
                headers={"apikey": config.api_key}
            )
            response.raise_for_status()
            
            return {
                "success": True,
                "message": "Conexão estabelecida com sucesso!",
                "status_code": response.status_code
            }
            
        except httpx.HTTPError as e:
            return {
                "success": False,
                "message": f"Erro ao conectar: {str(e)}",
                "status_code": getattr(e.response, 'status_code', 0) if hasattr(e, 'response') else 0
            }
        except Exception as e:
            return {
                "success": False,
                "message": f"Erro: {str(e)}",
                "status_code": 0
            }


# ============ CONEXÕES WHATSAPP ============

@router.get("/conexoes")
async def listar_conexoes(
    current_user: Usuario = Depends(get_current_user)
):
    """Lista conexões WhatsApp do usuário"""
    conexoes = await db.whatsapp_conexoes.find({
        "usuario_id": current_user.id,
        "deleted": {"$ne": True}
    }).to_list(100)
    
    # Converter ObjectId para string
    for conexao in conexoes:
        conexao["_id"] = str(conexao["_id"])
    
    return {"items": conexoes, "total": len(conexoes)}


@router.post("/conexoes")
async def criar_conexao(
    background_tasks: BackgroundTasks,
    current_user: Usuario = Depends(get_current_user)
):
    """Cria nova conexão WhatsApp e gera QR Code"""
    
    # Verificar se Evolution API está configurada
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    if not config_doc or not config_doc.get("dados", {}).get("habilitado"):
        raise HTTPException(400, "Evolution API não configurada. Entre em contato com o administrador.")
    
    config = EvolutionAPIConfig(**config_doc["dados"])
    
    # Criar instance_name único
    instance_name = f"user_{current_user.id[:8]}_{uuid.uuid4().hex[:8]}"
    
    # Criar instância na Evolution API
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{config.api_url}/instance/create",
                headers={"apikey": config.api_key},
                json={
                    "instanceName": instance_name,
                    "qrcode": True,
                    "integration": "WHATSAPP-BAILEYS"
                }
            )
            response.raise_for_status()
            result = response.json()
            
        except Exception as e:
            raise HTTPException(500, f"Erro ao criar instância na Evolution API: {str(e)}")
    
    # Aguardar e buscar QR Code via /instance/connect
    qr_code = None
    await asyncio.sleep(3)  # Aguardar 3 segundos para instância iniciar
    try:
        async with httpx.AsyncClient(timeout=15) as qr_client:
            qr_response = await qr_client.get(
                f"{config.api_url}/instance/connect/{instance_name}",
                headers={"apikey": config.api_key}
            )
            if qr_response.status_code == 200:
                qr_result = qr_response.json()
                qr_code = qr_result.get("base64")
    except Exception as e:
        print(f"Erro ao buscar QR Code: {str(e)}")
        pass  # Se falhar, continuará sem QR Code e será buscado depois
    
    # Salvar conexão no banco
    conexao = WhatsAppConexao(
        usuario_id=current_user.id,
        instance_name=instance_name,
        instance_id=result.get("instance", {}).get("instanceId"),
        qr_code=qr_code,
        qr_code_expiracao=datetime.now(timezone.utc) + timedelta(minutes=2),
        status="qrcode" if qr_code else "desconectado"
    )
    
    await db.whatsapp_conexoes.insert_one(conexao.model_dump())
    
    # Agendar verificação de status
    background_tasks.add_task(verificar_status_conexao, conexao.id, config)
    
    # Converter _id para string
    conexao_dict = conexao.model_dump()
    
    return conexao_dict


@router.get("/conexoes/{conexao_id}/qrcode")
async def obter_qrcode(
    conexao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém QR Code atualizado"""
    conexao = await db.whatsapp_conexoes.find_one({
        "id": conexao_id,
        "usuario_id": current_user.id
    })
    
    if not conexao:
        raise HTTPException(404, "Conexão não encontrada")
    
    # Buscar QR Code atualizado da Evolution API
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    config = EvolutionAPIConfig(**config_doc["dados"])
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                f"{config.api_url}/instance/connect/{conexao['instance_name']}",
                headers={"apikey": config.api_key}
            )
            result = response.json()
            
            # Atualizar QR Code no banco
            await db.whatsapp_conexoes.update_one(
                {"id": conexao_id},
                {"$set": {
                    "qr_code": result.get("base64"),
                    "qr_code_expiracao": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return {"qr_code": result.get("base64")}
            
        except Exception as e:
            raise HTTPException(500, f"Erro ao obter QR Code: {str(e)}")


@router.get("/conexoes/{conexao_id}/status")
async def verificar_status(
    conexao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Verifica status da conexão"""
    conexao = await db.whatsapp_conexoes.find_one({
        "id": conexao_id,
        "usuario_id": current_user.id
    })
    
    if not conexao:
        raise HTTPException(404, "Conexão não encontrada")
    
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    config = EvolutionAPIConfig(**config_doc["dados"])
    
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.get(
                f"{config.api_url}/instance/connectionState/{conexao['instance_name']}",
                headers={"apikey": config.api_key}
            )
            result = response.json()
            
            status_map = {
                "open": "conectado",
                "connecting": "qrcode",
                "close": "desconectado"
            }
            
            # Extrair state corretamente da resposta
            state = result.get("instance", {}).get("state")
            novo_status = status_map.get(state)
            
            # Se não reconhecer o state, manter status atual se tiver QR Code
            if not novo_status:
                if conexao.get("qr_code"):
                    novo_status = "qrcode"
                else:
                    novo_status = "desconectado"
            
            # Atualizar status
            await db.whatsapp_conexoes.update_one(
                {"id": conexao_id},
                {"$set": {
                    "status": novo_status,
                    "numero_telefone": result.get("instance", {}).get("phoneNumber"),
                    "data_conexao": datetime.now(timezone.utc).isoformat() if novo_status == "conectado" else None,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }}
            )
            
            return {"status": novo_status, "detalhes": result}
            
        except Exception as e:
            raise HTTPException(500, f"Erro ao verificar status: {str(e)}")


@router.delete("/conexoes/{conexao_id}")
async def deletar_conexao(
    conexao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Remove conexão WhatsApp"""
    conexao = await db.whatsapp_conexoes.find_one({
        "id": conexao_id,
        "usuario_id": current_user.id
    })
    
    if not conexao:
        raise HTTPException(404, "Conexão não encontrada")
    
    # Deletar instância na Evolution API
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    if config_doc:
        config = EvolutionAPIConfig(**config_doc["dados"])
        
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                await client.delete(
                    f"{config.api_url}/instance/delete/{conexao['instance_name']}",
                    headers={"apikey": config.api_key}
                )
            except:
                pass  # Continuar mesmo se falhar na API
    
    # Marcar como deletado no banco
    await db.whatsapp_conexoes.update_one(
        {"id": conexao_id},
        {"$set": {
            "deleted": True, 
            "ativo": False,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    return {"message": "Conexão removida com sucesso"}


# ============ ENVIO DE MENSAGENS ============

@router.post("/mensagens/enviar")
async def enviar_mensagem(
    request: EnviarMensagemRequest,
    current_user: Usuario = Depends(get_current_user)
):
    """Envia mensagem via WhatsApp"""
    
    # Buscar conexão ativa
    conexao = await db.whatsapp_conexoes.find_one({
        "usuario_id": current_user.id,
        "status": "conectado",
        "ativo": True,
        "deleted": {"$ne": True}
    })
    
    if not conexao:
        raise HTTPException(400, "Nenhuma conexão WhatsApp ativa. Conecte seu WhatsApp primeiro.")
    
    # Buscar configuração Evolution
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    config = EvolutionAPIConfig(**config_doc["dados"])
    
    # Criar registro da mensagem
    mensagem = WhatsAppMensagem(
        usuario_id=current_user.id,
        conexao_id=conexao["id"],
        cliente_id=request.cliente_id,
        emprestimo_id=request.emprestimo_id,
        parcela_id=request.parcela_id,
        numero_destino=request.numero_destino,
        mensagem=request.mensagem,
        tipo=request.tipo
    )
    
    # Enviar via Evolution API
    async with httpx.AsyncClient(timeout=30) as client:
        try:
            response = await client.post(
                f"{config.api_url}/message/sendText/{conexao['instance_name']}",
                headers={"apikey": config.api_key},
                json={
                    "number": request.numero_destino,
                    "text": request.mensagem
                }
            )
            response.raise_for_status()
            result = response.json()
            
            # Atualizar mensagem com sucesso
            mensagem.status = "enviado"
            mensagem.message_id = result.get("key", {}).get("id")
            mensagem.tentativas = 1
            
        except Exception as e:
            mensagem.status = "falha"
            mensagem.erro = str(e)
            mensagem.tentativas = 1
    
    # Salvar no banco
    await db.whatsapp_mensagens.insert_one(mensagem.model_dump())
    
    # Atualizar data_ultima_mensagem da conexão
    await db.whatsapp_conexoes.update_one(
        {"id": conexao["id"]},
        {"$set": {"data_ultima_mensagem": datetime.now(timezone.utc).isoformat()}}
    )
    
    return mensagem.model_dump()


@router.get("/mensagens")
async def listar_mensagens(
    cliente_id: str = None,
    limit: int = 50,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista histórico de mensagens"""
    filtro = {"usuario_id": current_user.id}
    
    if cliente_id:
        filtro["cliente_id"] = cliente_id
    
    mensagens = await db.whatsapp_mensagens.find(filtro) \
        .sort("data_envio", -1) \
        .limit(limit) \
        .to_list(limit)
    
    # Converter ObjectId para string
    for mensagem in mensagens:
        mensagem["_id"] = str(mensagem["_id"])
    
    return {"items": mensagens, "total": len(mensagens)}


# ============ FUNÇÕES AUXILIARES ============

async def verificar_status_conexao(conexao_id: str, config: EvolutionAPIConfig):
    """Verifica status da conexão periodicamente"""
    import asyncio
    
    for _ in range(12):  # 2 minutos (12 x 10s)
        await asyncio.sleep(10)
        
        conexao = await db.whatsapp_conexoes.find_one({"id": conexao_id})
        if not conexao or conexao.get("status") == "conectado":
            break
        
        # Verificar status na API
        async with httpx.AsyncClient(timeout=30) as client:
            try:
                response = await client.get(
                    f"{config.api_url}/instance/connectionState/{conexao['instance_name']}",
                    headers={"apikey": config.api_key}
                )
                result = response.json()
                
                # Extrair state corretamente da resposta
                state = result.get("instance", {}).get("state")
                
                # Mapear status
                if state == "open":
                    await db.whatsapp_conexoes.update_one(
                        {"id": conexao_id},
                        {"$set": {
                            "status": "conectado",
                            "numero_telefone": result.get("instance", {}).get("phoneNumber"),
                            "data_conexao": datetime.now(timezone.utc).isoformat(),
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
                    break
                elif state == "connecting":
                    # Manter como qrcode enquanto está conectando
                    await db.whatsapp_conexoes.update_one(
                        {"id": conexao_id},
                        {"$set": {
                            "status": "qrcode",
                            "updated_at": datetime.now(timezone.utc).isoformat()
                        }}
                    )
            except:
                pass


@router.post("/enviar-cobranca-parcela/{parcela_id}")
async def enviar_cobranca_parcela(
    parcela_id: str,
    usar_fila: bool = True,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Envia mensagem de cobrança via WhatsApp para uma parcela específica
    Usa Evolution API com sistema anti-spam integrado
    
    Params:
        parcela_id: ID da parcela
        usar_fila: True para adicionar na fila (recomendado), False para envio imediato
    """
    from services.whatsapp_service import enviar_notificacao_para_cliente, formatar_template_mensagem
    from services.whatsapp_anti_spam_service import WhatsAppAntiSpamService
    from services.whatsapp_fila_service import WhatsAppFilaService
    
    anti_spam = WhatsAppAntiSpamService(db)
    fila_service = WhatsAppFilaService(db)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": parcela_id,
        "usuario_id": current_user.id,
        "deleted": {"$ne": True}
    })
    
    if not parcela:
        raise HTTPException(404, "Parcela não encontrada")
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": parcela.get("emprestimo_id")
    })
    
    if not emprestimo:
        raise HTTPException(404, "Empréstimo não encontrado")
    
    # Buscar cliente
    cliente = await db.clientes.find_one({
        "id": emprestimo.get("cliente_id")
    })
    
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    
    # Verificar se cliente tem telefone
    telefone = cliente.get("telefone") or cliente.get("celular")
    if not telefone:
        raise HTTPException(400, "Cliente não possui telefone cadastrado")
    
    # Buscar configurações de notificação para obter template
    config = await db.configuracoes.find_one({
        "tipo": "notificacoes_vencimento",
        "usuario_id": current_user.id
    })
    
    # Template padrão ou personalizado
    if config and config.get("dados", {}).get("template_whatsapp"):
        template = config["dados"]["template_whatsapp"]
    else:
        template = (
            "Olá {cliente_nome}! 👋\n\n"
            "Lembrete de parcela:\n"
            "📅 Vencimento: {data_vencimento}\n"
            "💰 Valor: R$ {valor}\n"
            "📋 Parcela {numero_parcela}/{total_parcelas}\n\n"
            "Qualquer dúvida, estou à disposição!"
        )
    
    # Preparar dados para o template
    valor_devido = parcela.get("valor_total", 0) - parcela.get("valor_pago", 0)
    data_venc = parcela.get("data_vencimento", "")
    
    # Formatar data
    if data_venc:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(str(data_venc).replace('Z', '+00:00'))
            data_formatada = dt.strftime("%d/%m/%Y")
        except:
            data_formatada = str(data_venc)
    else:
        data_formatada = "N/A"
    
    mensagem = formatar_template_mensagem(template, {
        "cliente_nome": cliente.get("nome", "Cliente"),
        "numero_parcela": str(parcela.get("numero_parcela", "?")),
        "total_parcelas": str(emprestimo.get("prazo_meses", "?")),
        "valor": f"{valor_devido:,.2f}".replace(",", "X").replace(".", ",").replace("X", "."),
        "data_vencimento": data_formatada,
        "dias": "0"  # Para compatibilidade com template
    })
    
    # ===== SISTEMA ANTI-SPAM =====
    
    if usar_fila:
        # MODO FILA (Recomendado) - Adiciona na fila e processa gradualmente
        fila_id = await fila_service.adicionar_na_fila(
            usuario_id=current_user.id,
            numero_destino=telefone,
            mensagem=mensagem,
            cliente_id=cliente.get("id"),
            emprestimo_id=emprestimo.get("id"),
            parcela_id=parcela_id,
            tipo="cobranca_manual",
            prioridade=3  # Alta prioridade para envios manuais
        )
        
        return {
            "success": True,
            "message": "Mensagem adicionada na fila com sucesso",
            "modo": "fila",
            "fila_id": fila_id,
            "info": "A mensagem será enviada respeitando os limites anti-spam"
        }
    
    else:
        # MODO IMEDIATO - Verifica anti-spam e envia na hora (pode falhar se atingiu limite)
        pode_enviar = await anti_spam.pode_enviar(current_user.id)
        
        if not pode_enviar["pode_enviar"]:
            # Não pode enviar agora - retornar motivo
            proximo = pode_enviar.get("proximo_disponivel")
            return {
                "success": False,
                "message": f"Não pode enviar agora: {pode_enviar['razao']}",
                "pode_enviar": False,
                "razao": pode_enviar["razao"],
                "proximo_disponivel": proximo.isoformat() if proximo else None,
                "delay_recomendado": pode_enviar.get("delay_recomendado", 0),
                "sugestao": "Use o modo fila (usar_fila=true) para envio automático"
            }
        
        # Pode enviar - enviar via Evolution API
        resultado = await enviar_notificacao_para_cliente(
            usuario_id=current_user.id,
            cliente_id=cliente.get("id"),
            mensagem=mensagem
        )
        
        if not resultado.get("success"):
            await anti_spam.registrar_envio(current_user.id, sucesso=False)
            raise HTTPException(400, resultado.get("message", "Erro ao enviar mensagem"))
        
        # Registrar sucesso no anti-spam
        await anti_spam.registrar_envio(current_user.id, sucesso=True)
        
        # Registrar log adicional
        await db.whatsapp_mensagens_log.insert_one({
            "usuario_id": current_user.id,
            "parcela_id": parcela_id,
            "emprestimo_id": emprestimo.get("id"),
            "cliente_id": cliente.get("id"),
            "numero_destino": telefone,
            "mensagem": mensagem,
            "tipo": "cobranca_manual",
            "status": "enviado",
            "message_id": resultado.get("message_id"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": "Mensagem enviada com sucesso via WhatsApp",
            "modo": "imediato",
            "numero_enviado": resultado.get("numero_enviado"),
            "message_id": resultado.get("message_id"),
            "delay_recomendado": pode_enviar.get("delay_recomendado", 30)
        }


@router.post("/enviar-confirmacao-pagamento/{pagamento_id}")
async def enviar_confirmacao_pagamento(
    pagamento_id: str,
    usar_fila: bool = True,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Envia mensagem de confirmação de pagamento via WhatsApp
    
    Params:
        pagamento_id: ID do pagamento
        usar_fila: True para adicionar na fila (recomendado), False para envio imediato
    """
    from services.whatsapp_service import enviar_notificacao_para_cliente
    from services.whatsapp_anti_spam_service import WhatsAppAntiSpamService
    from services.whatsapp_fila_service import WhatsAppFilaService
    
    anti_spam = WhatsAppAntiSpamService(db)
    fila_service = WhatsAppFilaService(db)
    
    # Buscar pagamento
    pagamento = await db.pagamentos.find_one({
        "id": pagamento_id,
        "usuario_id": current_user.id,
        "deleted": {"$ne": True}
    })
    
    if not pagamento:
        raise HTTPException(404, "Pagamento não encontrado")
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": pagamento.get("emprestimo_id")
    })
    
    if not emprestimo:
        raise HTTPException(404, "Empréstimo não encontrado")
    
    # Buscar cliente
    cliente = await db.clientes.find_one({
        "id": emprestimo.get("cliente_id")
    })
    
    if not cliente:
        raise HTTPException(404, "Cliente não encontrado")
    
    # Verificar se cliente tem telefone
    telefone = cliente.get("telefone") or cliente.get("celular")
    if not telefone:
        raise HTTPException(400, "Cliente não possui telefone cadastrado")
    
    # Buscar parcela para informações adicionais
    parcela = await db.parcelas.find_one({
        "id": pagamento.get("parcela_id")
    })
    
    # Formatar data do pagamento
    from utils.timezone_utils import format_datetime_br
    data_pagamento_obj = pagamento.get("data_pagamento")
    if isinstance(data_pagamento_obj, str):
        data_pagamento_obj = datetime.fromisoformat(data_pagamento_obj.replace('Z', '+00:00'))
    data_pagamento_formatada = format_datetime_br(data_pagamento_obj, format_type="completo")
    
    # Criar mensagem de confirmação
    mensagem = (
        f"✅ *PAGAMENTO CONFIRMADO!*\n\n"
        f"Olá *{cliente.get('nome', 'Cliente')}*! 👋\n\n"
        f"Confirmamos o recebimento do seu pagamento:\n\n"
        f"💰 *Valor Pago:* R$ {pagamento.get('valor_pago', 0):.2f}\n"
        f"📅 *Data/Hora:* {data_pagamento_formatada}\n"
        f"💳 *Método:* {pagamento.get('metodo_pagamento', 'N/A').upper()}\n"
    )
    
    # Adicionar informações da parcela se disponível
    if parcela:
        mensagem += f"📋 *Parcela:* {parcela.get('numero_parcela', '?')}/{emprestimo.get('prazo_meses', '?')}\n"
    
    # Adicionar observações se houver
    if pagamento.get("observacoes"):
        mensagem += f"\n📝 *Observações:* {pagamento.get('observacoes')}\n"
    
    mensagem += "\n✨ Obrigado pela confiança!\n\nQualquer dúvida, estou à disposição."
    
    # Modo fila (recomendado) - adiciona na fila e retorna
    if usar_fila:
        try:
            mensagem_id = str(uuid.uuid4())
            await fila_service.adicionar_na_fila(
                usuario_id=current_user.id,
                cliente_id=cliente.get("id"),
                telefone=telefone,
                mensagem=mensagem,
                tipo="confirmacao_pagamento",
                referencia_id=pagamento_id,
                mensagem_id=mensagem_id
            )
            
            return {
                "success": True,
                "message": "Mensagem adicionada à fila com sucesso. Será enviada automaticamente.",
                "modo": "fila",
                "mensagem_id": mensagem_id,
                "posicao_fila": await fila_service.contar_pendentes(current_user.id)
            }
        except Exception as e:
            raise HTTPException(500, f"Erro ao adicionar na fila: {str(e)}")
    
    # Modo imediato - verifica anti-spam e envia
    else:
        # Verificar se pode enviar (anti-spam)
        pode_enviar = await anti_spam.pode_enviar_mensagem(current_user.id)
        
        if not pode_enviar.get("pode_enviar"):
            # Não pode enviar agora - retornar motivo
            proximo = pode_enviar.get("proximo_disponivel")
            return {
                "success": False,
                "message": f"Não pode enviar agora: {pode_enviar['razao']}",
                "pode_enviar": False,
                "razao": pode_enviar["razao"],
                "proximo_disponivel": proximo.isoformat() if proximo else None,
                "delay_recomendado": pode_enviar.get("delay_recomendado", 0),
                "sugestao": "Use o modo fila (usar_fila=true) para envio automático"
            }
        
        # Pode enviar - enviar via Evolution API
        resultado = await enviar_notificacao_para_cliente(
            usuario_id=current_user.id,
            cliente_id=cliente.get("id"),
            mensagem=mensagem
        )
        
        if not resultado.get("success"):
            await anti_spam.registrar_envio(current_user.id, sucesso=False)
            raise HTTPException(400, resultado.get("message", "Erro ao enviar mensagem"))
        
        # Registrar sucesso no anti-spam
        await anti_spam.registrar_envio(current_user.id, sucesso=True)
        
        # Registrar log adicional
        await db.whatsapp_mensagens_log.insert_one({
            "usuario_id": current_user.id,
            "pagamento_id": pagamento_id,
            "emprestimo_id": emprestimo.get("id"),
            "cliente_id": cliente.get("id"),
            "numero_destino": telefone,
            "mensagem": mensagem,
            "tipo": "confirmacao_pagamento",
            "status": "enviado",
            "message_id": resultado.get("message_id"),
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return {
            "success": True,
            "message": "Confirmação de pagamento enviada com sucesso via WhatsApp",
            "modo": "imediato",
            "numero_enviado": resultado.get("numero_enviado"),
            "message_id": resultado.get("message_id"),
            "delay_recomendado": pode_enviar.get("delay_recomendado", 30)
        }

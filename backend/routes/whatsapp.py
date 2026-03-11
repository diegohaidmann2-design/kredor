"""
Rotas WhatsApp - Gestão de conexões e envio de mensagens
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from datetime import datetime, timedelta, timezone
import httpx
import uuid

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
    
    # Salvar conexão no banco
    conexao = WhatsAppConexao(
        usuario_id=current_user.id,
        instance_name=instance_name,
        instance_id=result.get("instance", {}).get("instanceId"),
        qr_code=result.get("qrcode", {}).get("base64"),
        qr_code_expiracao=datetime.now(timezone.utc) + timedelta(minutes=2),
        status="qrcode"
    )
    
    await db.whatsapp_conexoes.insert_one(conexao.model_dump())
    
    # Agendar verificação de status
    background_tasks.add_task(verificar_status_conexao, conexao.id, config)
    
    return conexao.model_dump()


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
                f"{config.api_url}/instance/qrcode/{conexao['instance_name']}",
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
            
            novo_status = status_map.get(result.get("state"), "desconectado")
            
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
                
                if result.get("state") == "open":
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
            except:
                pass

"""
Serviço de WhatsApp - Sistema Gestor Cred
Funções para enviar mensagens WhatsApp via Evolution API
"""
import httpx
from typing import Optional, Dict
from config import db


async def get_evolution_config():
    """Busca configurações da Evolution API"""
    config_doc = await db.configuracoes.find_one({"tipo": "evolution_api"})
    if not config_doc:
        return None
    return config_doc.get("dados", {})


async def enviar_mensagem_whatsapp(
    usuario_id: str,
    numero_destino: str,
    mensagem: str
) -> Dict:
    """
    Envia mensagem WhatsApp para um número específico
    
    Args:
        usuario_id: ID do usuário (dono da conexão WhatsApp)
        numero_destino: Número de telefone do destinatário (com DDI)
        mensagem: Texto da mensagem a ser enviada
        
    Returns:
        Dict com resultado do envio (success, error, message_id)
    """
    try:
        # 1. Buscar conexão WhatsApp ativa do usuário
        conexao = await db.whatsapp_conexoes.find_one({
            "usuario_id": usuario_id,
            "status": "conectado",
            "deleted": {"$ne": True}
        }, sort=[("ativo", -1), ("updated_at", -1)])
        
        if not conexao:
            return {
                "success": False,
                "error": "whatsapp_nao_conectado",
                "message": "WhatsApp não está conectado"
            }
        
        instance_name = conexao.get("instance_name")
        
        # 2. Buscar configurações da Evolution API
        config = await get_evolution_config()
        if not config or not config.get("habilitado"):
            return {
                "success": False,
                "error": "evolution_nao_configurada",
                "message": "Evolution API não está configurada"
            }
        
        api_url = config.get("api_url")
        api_key = config.get("api_key")
        timeout = config.get("timeout", 30)
        
        # 3. Limpar e formatar número (remover caracteres especiais)
        numero_limpo = ''.join(filter(str.isdigit, numero_destino))
        
        # Se não tiver DDI (código do país), adicionar 55 (Brasil)
        if not numero_limpo.startswith('55'):
            numero_limpo = '55' + numero_limpo
        
        # 4. Enviar mensagem via Evolution API
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{api_url}/message/sendText/{instance_name}",
                headers={"apikey": api_key},
                json={
                    "number": numero_limpo,
                    "text": mensagem
                }
            )
            
            response.raise_for_status()
            result = response.json()
            
            # 5. Registrar log de envio
            from datetime import datetime, timezone
            await db.whatsapp_mensagens_log.insert_one({
                "usuario_id": usuario_id,
                "instance_name": instance_name,
                "numero_destino": numero_limpo,
                "mensagem": mensagem,
                "status": "enviado",
                "response": result,
                "created_at": datetime.now(timezone.utc).isoformat()
            })
            
            return {
                "success": True,
                "message_id": result.get("key", {}).get("id"),
                "numero_enviado": numero_limpo,
                "status_envio": result.get("status")
            }
            
    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e, 'response') else str(e)
        
        # Log de erro
        await db.whatsapp_mensagens_log.insert_one({
            "usuario_id": usuario_id,
            "numero_destino": numero_destino,
            "mensagem": mensagem,
            "status": "erro",
            "erro": error_detail,
            "created_at": None
        })
        
        return {
            "success": False,
            "error": "erro_envio",
            "message": f"Erro ao enviar mensagem: {error_detail}"
        }
        
    except Exception as e:
        # Log de erro genérico
        await db.whatsapp_mensagens_log.insert_one({
            "usuario_id": usuario_id,
            "numero_destino": numero_destino,
            "mensagem": mensagem,
            "status": "erro",
            "erro": str(e),
            "created_at": None
        })
        
        return {
            "success": False,
            "error": "erro_geral",
            "message": str(e)
        }


async def enviar_documento_whatsapp(
    usuario_id: str,
    numero_destino: str,
    base64_documento: str,
    nome_arquivo: str,
    legenda: str = ""
) -> Dict:
    """
    Envia um documento (PDF) via WhatsApp usando a Evolution API (/message/sendMedia).

    Args:
        usuario_id: ID do usuário (dono da conexão WhatsApp)
        numero_destino: Número do destinatário (com ou sem DDI)
        base64_documento: Conteúdo do arquivo em base64 (sem prefixo data:)
        nome_arquivo: Nome do arquivo (ex: comprovante.pdf)
        legenda: Texto opcional que acompanha o documento

    Returns:
        Dict com resultado do envio (success, error, message_id)
    """
    from datetime import datetime, timezone
    try:
        conexao = await db.whatsapp_conexoes.find_one({
            "usuario_id": usuario_id,
            "status": "conectado",
            "deleted": {"$ne": True}
        }, sort=[("ativo", -1), ("updated_at", -1)])
        if not conexao:
            return {
                "success": False,
                "error": "whatsapp_nao_conectado",
                "message": "WhatsApp não está conectado"
            }

        instance_name = conexao.get("instance_name")

        config = await get_evolution_config()
        if not config or not config.get("habilitado"):
            return {
                "success": False,
                "error": "evolution_nao_configurada",
                "message": "Evolution API não está configurada"
            }

        api_url = config.get("api_url")
        api_key = config.get("api_key")
        timeout = config.get("timeout", 60)

        numero_limpo = ''.join(filter(str.isdigit, numero_destino))
        if not numero_limpo.startswith('55'):
            numero_limpo = '55' + numero_limpo

        payload = {
            "number": numero_limpo,
            "mediatype": "document",
            "mimetype": "application/pdf",
            "media": base64_documento,
            "fileName": nome_arquivo,
        }
        if legenda:
            payload["caption"] = legenda

        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                f"{api_url}/message/sendMedia/{instance_name}",
                headers={"apikey": api_key},
                json=payload
            )
            response.raise_for_status()
            result = response.json()

            await db.whatsapp_mensagens_log.insert_one({
                "usuario_id": usuario_id,
                "instance_name": instance_name,
                "numero_destino": numero_limpo,
                "mensagem": f"[documento] {nome_arquivo}",
                "status": "enviado",
                "response": result,
                "created_at": datetime.now(timezone.utc).isoformat()
            })

            return {
                "success": True,
                "message_id": result.get("key", {}).get("id"),
                "numero_enviado": numero_limpo,
                "status_envio": result.get("status")
            }

    except httpx.HTTPStatusError as e:
        error_detail = e.response.text if hasattr(e, 'response') else str(e)
        return {
            "success": False,
            "error": "erro_envio",
            "message": f"Erro ao enviar documento: {error_detail}"
        }
    except Exception as e:
        return {
            "success": False,
            "error": "erro_geral",
            "message": str(e)
        }


async def enviar_notificacao_para_cliente(
    usuario_id: str,
    cliente_id: str,
    mensagem: str
) -> Dict:
    """
    Envia notificação WhatsApp para um cliente específico
    
    Args:
        usuario_id: ID do usuário (gestor)
        cliente_id: ID do cliente que receberá a mensagem
        mensagem: Texto da mensagem
        
    Returns:
        Dict com resultado do envio
    """
    try:
        # Buscar telefone do cliente
        cliente = await db.clientes.find_one({"id": cliente_id})
        
        if not cliente:
            return {
                "success": False,
                "error": "cliente_nao_encontrado",
                "message": "Cliente não encontrado"
            }
        
        telefone = cliente.get("telefone") or cliente.get("celular")
        
        if not telefone:
            return {
                "success": False,
                "error": "telefone_nao_cadastrado",
                "message": "Cliente não possui telefone cadastrado"
            }
        
        # Enviar mensagem
        resultado = await enviar_mensagem_whatsapp(
            usuario_id=usuario_id,
            numero_destino=telefone,
            mensagem=mensagem
        )
        
        return resultado
        
    except Exception as e:
        return {
            "success": False,
            "error": "erro_geral",
            "message": str(e)
        }


def formatar_template_mensagem(template: str, dados: Dict) -> str:
    """
    Formata template de mensagem substituindo variáveis
    
    Args:
        template: String com variáveis entre chaves {variavel}
        dados: Dicionário com valores das variáveis
        
    Returns:
        String formatada
        
    Exemplo:
        template = "Olá {cliente_nome}, parcela #{numero} de R$ {valor}"
        dados = {"cliente_nome": "João", "numero": "1", "valor": "100,00"}
        resultado = "Olá João, parcela #1 de R$ 100,00"
    """
    try:
        return template.format(**dados)
    except KeyError as e:
        # Se alguma variável não existir, retornar template original
        print(f"Variável não encontrada no template: {e}")
        return template
    except Exception as e:
        print(f"Erro ao formatar template: {e}")
        return template

"""
Serviço de Assinaturas com Mercado Pago
Suporta: Cartão e PIX recorrente
"""
import os
import httpx
from typing import Optional, Dict, Any
from datetime import datetime, timedelta


MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
MERCADOPAGO_API_URL = "https://api.mercadopago.com/v1"


class MercadoPagoAssinaturaError(Exception):
    """Exceção para erros do Mercado Pago"""
    pass


async def criar_plano_mp(plano_id: str, nome: str, preco: float) -> Dict[str, Any]:
    """
    Cria um plano de assinatura no Mercado Pago
    """
    url = f"{MERCADOPAGO_API_URL}/plans"
    
    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "reason": f"Kredor - {nome}",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "transaction_amount": preco,
            "currency_id": "BRL"
        },
        "back_url": f"{os.environ.get('APP_URL', '')}/assinatura",
        "external_reference": plano_id
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers)
        
        if response.status_code == 201:
            return response.json()
        else:
            raise MercadoPagoAssinaturaError(f"Erro ao criar plano: {response.text}")


async def criar_assinatura_mp(
    email: str,
    plano_id: str,
    nome: str,
    preco: float,
    metadata: Dict[str, str] = None
) -> Dict[str, Any]:
    """
    Cria uma assinatura para um usuário
    Retorna link de pagamento (PIX ou Cartão)
    """
    url = f"{MERCADOPAGO_API_URL}/preapproval"
    
    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    # Data de início: agora
    start_date = datetime.utcnow().isoformat() + "Z"
    
    data = {
        "reason": f"Kredor - Plano {nome}",
        "payer_email": email,
        "back_url": f"{os.environ.get('APP_URL', '')}/assinatura?status=success",
        "auto_recurring": {
            "frequency": 1,
            "frequency_type": "months",
            "start_date": start_date,
            "transaction_amount": preco,
            "currency_id": "BRL"
        },
        "external_reference": metadata.get('usuario_id', '') if metadata else '',
        "status": "pending"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=data, headers=headers, timeout=30.0)
        
        if response.status_code == 201:
            result = response.json()
            return {
                "id": result.get("id"),
                "init_point": result.get("init_point"),  # Link de pagamento
                "status": result.get("status"),
                "external_reference": result.get("external_reference")
            }
        else:
            raise MercadoPagoAssinaturaError(f"Erro ao criar assinatura: {response.text}")


async def obter_assinatura_mp(assinatura_id: str) -> Dict[str, Any]:
    """
    Obtém detalhes de uma assinatura
    """
    url = f"{MERCADOPAGO_API_URL}/preapproval/{assinatura_id}"
    
    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        
        if response.status_code == 200:
            return response.json()
        else:
            raise MercadoPagoAssinaturaError(f"Erro ao obter assinatura: {response.text}")


async def cancelar_assinatura_mp(assinatura_id: str) -> bool:
    """
    Cancela uma assinatura
    """
    url = f"{MERCADOPAGO_API_URL}/preapproval/{assinatura_id}"
    
    headers = {
        "Authorization": f"Bearer {MERCADOPAGO_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    data = {
        "status": "cancelled"
    }
    
    async with httpx.AsyncClient() as client:
        response = await client.put(url, json=data, headers=headers)
        
        if response.status_code == 200:
            return True
        else:
            raise MercadoPagoAssinaturaError(f"Erro ao cancelar assinatura: {response.text}")


async def verificar_status_assinatura_mp(assinatura_id: str) -> Dict[str, Any]:
    """
    Verifica status de uma assinatura
    
    Status possíveis:
    - pending: Pendente de pagamento
    - authorized: Assinatura ativa
    - paused: Pausada
    - cancelled: Cancelada
    """
    assinatura = await obter_assinatura_mp(assinatura_id)
    
    return {
        "id": assinatura.get("id"),
        "status": assinatura.get("status"),
        "payer_email": assinatura.get("payer_email"),
        "reason": assinatura.get("reason"),
        "transaction_amount": assinatura.get("auto_recurring", {}).get("transaction_amount"),
        "next_payment_date": assinatura.get("next_payment_date"),
        "external_reference": assinatura.get("external_reference")
    }

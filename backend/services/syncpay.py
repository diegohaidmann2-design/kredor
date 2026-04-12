"""
SyncPay PIX Integration Service
Based on official docs: https://syncpay.apidog.io
"""
import httpx
import logging
import os
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from config import db

logger = logging.getLogger(__name__)

# Cache de token em memória (prod usar Redis)
_token_cache = {"token": None, "expires_at": None}

class SyncPayService:
    BASE_URL = "https://api.syncpayments.com.br"
    
    def __init__(self, client_id: str, client_secret: str):
        if not client_id or not client_secret:
            raise ValueError("client_id e client_secret são obrigatórios")
        self.client_id = client_id
        self.client_secret = client_secret
    
    async def _get_token(self) -> str:
        """Obtém token bearer (cacheia por 55min para segurança)"""
        now = datetime.now(timezone.utc)
        
        # Usar cache se válido
        if _token_cache["token"] and _token_cache["expires_at"] and now < _token_cache["expires_at"]:
            return _token_cache["token"]
        
        # Gerar novo token
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/partner/v1/auth-token",
                    json={"client_id": self.client_id, "client_secret": self.client_secret}
                )
                response.raise_for_status()
                data = response.json()
                
                token = data["access_token"]
                expires_in = data.get("expires_in", 3600)
                
                # Cache por 55min (buffer de 5min)
                _token_cache["token"] = token
                _token_cache["expires_at"] = now + timedelta(seconds=expires_in - 300)
                
                logger.info("SyncPay token obtido com sucesso")
                return token
        except Exception as e:
            logger.error(f"Erro ao obter token SyncPay: {e}")
            raise
    
    async def criar_cobranca_pix(
        self,
        valor: float,
        descricao: str,
        external_id: str,
        customer_name: Optional[str] = None,
        customer_cpf: Optional[str] = None,
        customer_email: Optional[str] = None,
        customer_phone: Optional[str] = None,
        webhook_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria cobrança PIX (CashIn) via SyncPay v2 API
        
        Endpoint: POST /api/partner/v1/cash-in
        
        Retorna:
            {
                "message": "Cashin request successfully submitted",
                "pix_code": "00020126...",
                "identifier": "3df0319d-..."
            }
        """
        token = await self._get_token()
        
        payload = {
            "amount": float(valor),
            "description": (descricao or "Pagamento PIX")[:200],
        }
        
        # Webhook URL
        if webhook_url:
            payload["webhook_url"] = webhook_url
        
        # Dados do cliente
        if customer_name:
            client_data = {"name": customer_name}
            if customer_cpf:
                client_data["cpf"] = customer_cpf.replace(".", "").replace("-", "")
            if customer_email:
                client_data["email"] = customer_email
            if customer_phone:
                client_data["phone"] = customer_phone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
            payload["client"] = client_data
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/partner/v1/cash-in",
                    headers={
                        "Authorization": f"Bearer {token}",
                        "Accept": "application/json",
                        "Content-Type": "application/json"
                    },
                    json=payload
                )
                response.raise_for_status()
                data = response.json()
                
                logger.info(f"SyncPay CashIn criado: {data.get('identifier')}")
                
                # Normalizar resposta
                return {
                    "identifier": data.get("identifier", ""),
                    "pix_code": data.get("pix_code", ""),
                    "message": data.get("message", ""),
                    "status": "pending"
                }
        except httpx.HTTPStatusError as e:
            logger.error(f"SyncPay API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar cobrança SyncPay: {e}")
            raise
    
    async def consultar_transacao(self, identifier: str) -> Dict[str, Any]:
        """
        Consulta status da transação
        Endpoint: GET /api/partner/v1/transaction/{identifier}
        
        Status possíveis: pending, completed, failed, refunded, med
        """
        token = await self._get_token()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/partner/v1/transaction/{identifier}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                result = response.json()
                
                # Resposta vem em result["data"]
                data = result.get("data", result)
                return {
                    "identifier": data.get("reference_id", identifier),
                    "status": data.get("status", "pending"),
                    "amount": data.get("amount", 0),
                    "currency": data.get("currency", "BRL"),
                    "transaction_date": data.get("transaction_date"),
                    "description": data.get("description"),
                    "pix_code": data.get("pix_code")
                }
        except Exception as e:
            logger.error(f"Erro ao consultar transação SyncPay: {e}")
            raise
    
    async def consultar_saldo(self) -> Dict[str, Any]:
        """Retorna saldo da conta SyncPay"""
        token = await self._get_token()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/partner/v1/balance",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return response.json()
        except Exception as e:
            logger.error(f"Erro ao consultar saldo SyncPay: {e}")
            raise


async def obter_syncpay_service() -> Optional[SyncPayService]:
    """Factory: carrega config do DB e retorna service"""
    config = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
    
    if not config or not config.get("dados", {}).get("syncpay_habilitado"):
        return None
    
    dados = config["dados"]
    client_id = dados.get("syncpay_client_id")
    client_secret = dados.get("syncpay_client_secret")
    
    if not client_id or not client_secret:
        logger.warning("SyncPay habilitado mas credenciais ausentes")
        return None
    
    return SyncPayService(client_id, client_secret)

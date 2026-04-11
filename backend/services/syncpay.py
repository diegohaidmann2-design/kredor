"""
SyncPay PIX Integration Service
"""
import httpx
import logging
from datetime import datetime, timedelta
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
        now = datetime.utcnow()
        
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
        customer_document: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Cria cobrança PIX (CashIn)
        
        Retorna:
            {
                "transaction_id": "abc123",
                "qr_code": "00020126...",
                "qr_code_url": "https://...",
                "expires_at": "2025-06-22T...",
                "amount": 100.00,
                "status": "pending"
            }
        """
        token = await self._get_token()
        
        payload = {
            "amount": valor,
            "description": descricao[:200],  # Limite API
            "external_reference": external_id,
        }
        
        if customer_name:
            payload["customer"] = {"name": customer_name}
            if customer_document:
                payload["customer"]["document"] = customer_document
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.BASE_URL}/api/partner/v1/pix/cashin",
                    headers={"Authorization": f"Bearer {token}"},
                    json=payload
                )
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"SyncPay API error: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Erro ao criar cobrança SyncPay: {e}")
            raise
    
    async def consultar_transacao(self, transaction_id: str) -> Dict[str, Any]:
        """Consulta status da transação"""
        token = await self._get_token()
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{self.BASE_URL}/api/partner/v1/transactions/{transaction_id}",
                    headers={"Authorization": f"Bearer {token}"}
                )
                response.raise_for_status()
                return response.json()
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
    config = await db.configuracoes.find_one({"tipo": "gateway_assinatura"})
    
    if not config or not config.get("dados", {}).get("syncpay_habilitado"):
        return None
    
    dados = config["dados"]
    client_id = dados.get("syncpay_client_id")
    client_secret = dados.get("syncpay_client_secret")
    
    if not client_id or not client_secret:
        logger.warning("SyncPay habilitado mas credenciais ausentes")
        return None
    
    return SyncPayService(client_id, client_secret)

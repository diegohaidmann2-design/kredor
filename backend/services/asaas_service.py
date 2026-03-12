"""
Serviço de integração com Asaas - Gateway de pagamentos brasileiro
Suporta PIX, Boleto e Cartão de Crédito
"""
import httpx
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import logging

from config import db

logger = logging.getLogger(__name__)


class AsaasService:
    """Serviço para integração com a API do Asaas"""
    
    def __init__(self):
        self.base_url = "https://api.asaas.com/v3"
        self.base_url_sandbox = "https://sandbox.asaas.com/api/v3"
    
    async def _get_config(self) -> Optional[Dict[str, Any]]:
        """Busca configuração do Asaas no banco de dados"""
        # Buscar config de gateway de assinaturas
        config = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
        if config and config.get("dados"):
            dados = config["dados"]
            if dados.get("asaas_habilitado"):
                return {
                    "habilitado": dados.get("asaas_habilitado", False),
                    "api_key": dados.get("asaas_api_key", ""),
                    "ambiente": dados.get("asaas_ambiente", "sandbox")
                }
        return None
    
    async def _get_headers(self) -> Dict[str, str]:
        """Retorna headers com a API key do banco"""
        config = await self._get_config()
        
        if not config or not config.get("habilitado"):
            raise Exception("Asaas não está habilitado. Configure em Configurações > Asaas")
        
        api_key = config.get("api_key")
        if not api_key:
            raise Exception("API Key do Asaas não configurada")
        
        return {
            "access_token": api_key,
            "Content-Type": "application/json"
        }
    
    async def _get_base_url(self) -> str:
        """Retorna URL base (sandbox ou produção)"""
        config = await self._get_config()
        if config and config.get("ambiente") == "producao":
            return self.base_url
        return self.base_url_sandbox
    
    async def testar_conexao(self, api_key: str, ambiente: str = "sandbox") -> Dict[str, Any]:
        """Testa conexão com Asaas"""
        try:
            base_url = self.base_url if ambiente == "producao" else self.base_url_sandbox
            headers = {
                "access_token": api_key,
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(
                    f"{base_url}/myAccount",
                    headers=headers
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "message": "Conexão estabelecida com sucesso!",
                        "conta": data.get("name", "Conta Asaas"),
                        "email": data.get("email", "")
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Erro na autenticação: {response.status_code}",
                        "detalhe": response.text
                    }
        except Exception as e:
            logger.error(f"Erro ao testar Asaas: {e}")
            return {
                "success": False,
                "message": f"Erro ao conectar: {str(e)}"
            }
    
    async def criar_cliente(self, nome: str, email: str, cpf_cnpj: str, 
                           telefone: Optional[str] = None) -> Dict[str, Any]:
        """Cria cliente no Asaas"""
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            # Limpar CPF/CNPJ
            cpf_cnpj_limpo = cpf_cnpj.replace(".", "").replace("-", "").replace("/", "")
            
            payload = {
                "name": nome,
                "email": email,
                "cpfCnpj": cpf_cnpj_limpo,
                "notificationDisabled": False
            }
            
            if telefone:
                telefone_limpo = telefone.replace("(", "").replace(")", "").replace("-", "").replace(" ", "")
                payload["mobilePhone"] = telefone_limpo
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/customers",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"Erro ao criar cliente Asaas: {response.text}")
                    raise Exception(f"Erro ao criar cliente: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao criar cliente Asaas: {e}")
            raise
    
    async def criar_cobranca(self, customer_id: str, valor: float, 
                            descricao: str, vencimento: str,
                            metodo_pagamento: str = "UNDEFINED") -> Dict[str, Any]:
        """
        Cria cobrança no Asaas
        
        Args:
            customer_id: ID do cliente no Asaas
            valor: Valor em reais (ex: 49.90)
            descricao: Descrição da cobrança
            vencimento: Data de vencimento (formato: YYYY-MM-DD)
            metodo_pagamento: UNDEFINED, PIX, BOLETO, CREDIT_CARD
        """
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            payload = {
                "customer": customer_id,
                "billingType": metodo_pagamento,
                "value": valor,
                "dueDate": vencimento,
                "description": descricao,
                "externalReference": f"assinatura_{customer_id}_{datetime.now(timezone.utc).timestamp()}",
                "postalService": False
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/payments",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"Erro ao criar cobrança Asaas: {response.text}")
                    raise Exception(f"Erro ao criar cobrança: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao criar cobrança Asaas: {e}")
            raise
    
    async def criar_assinatura(self, customer_id: str, valor: float, 
                              descricao: str, ciclo: str = "MONTHLY",
                              metodo_pagamento: str = "UNDEFINED") -> Dict[str, Any]:
        """
        Cria assinatura recorrente no Asaas
        
        Args:
            customer_id: ID do cliente no Asaas
            valor: Valor mensal em reais
            descricao: Descrição da assinatura
            ciclo: WEEKLY, BIWEEKLY, MONTHLY, QUARTERLY, SEMIANNUALLY, YEARLY
            metodo_pagamento: UNDEFINED, PIX, BOLETO, CREDIT_CARD
        """
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            # Calcular próxima data de vencimento (30 dias)
            proxima_data = (datetime.now(timezone.utc) + timedelta(days=30)).strftime("%Y-%m-%d")
            
            payload = {
                "customer": customer_id,
                "billingType": metodo_pagamento,
                "value": valor,
                "nextDueDate": proxima_data,
                "cycle": ciclo,
                "description": descricao,
                "externalReference": f"sub_{customer_id}_{datetime.now(timezone.utc).timestamp()}"
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{base_url}/subscriptions",
                    headers=headers,
                    json=payload
                )
                
                if response.status_code in [200, 201]:
                    return response.json()
                else:
                    logger.error(f"Erro ao criar assinatura Asaas: {response.text}")
                    raise Exception(f"Erro ao criar assinatura: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao criar assinatura Asaas: {e}")
            raise
    
    async def buscar_cobranca(self, payment_id: str) -> Dict[str, Any]:
        """Busca detalhes de uma cobrança"""
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/payments/{payment_id}",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Erro ao buscar cobrança: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao buscar cobrança Asaas: {e}")
            raise
    
    async def cancelar_assinatura(self, subscription_id: str) -> Dict[str, Any]:
        """Cancela assinatura no Asaas"""
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.delete(
                    f"{base_url}/subscriptions/{subscription_id}",
                    headers=headers
                )
                
                if response.status_code in [200, 204]:
                    return {"success": True, "message": "Assinatura cancelada"}
                else:
                    raise Exception(f"Erro ao cancelar assinatura: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao cancelar assinatura Asaas: {e}")
            raise
    
    async def obter_qrcode_pix(self, payment_id: str) -> Dict[str, Any]:
        """Obtém QR Code PIX para pagamento"""
        try:
            headers = await self._get_headers()
            base_url = await self._get_base_url()
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(
                    f"{base_url}/payments/{payment_id}/pixQrCode",
                    headers=headers
                )
                
                if response.status_code == 200:
                    return response.json()
                else:
                    raise Exception(f"Erro ao obter QR Code PIX: {response.text}")
                    
        except Exception as e:
            logger.error(f"Erro ao obter QR Code PIX: {e}")
            raise
    
    async def obter_link_boleto(self, payment_id: str) -> Optional[str]:
        """Obtém link do boleto bancário"""
        try:
            cobranca = await self.buscar_cobranca(payment_id)
            return cobranca.get("bankSlipUrl")
        except Exception as e:
            logger.error(f"Erro ao obter link do boleto: {e}")
            return None


# Instância global
asaas_service = AsaasService()

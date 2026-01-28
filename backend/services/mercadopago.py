"""
Serviço de Mercado Pago
"""
import httpx
import os
import logging
from typing import Dict, Any, Optional
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

MERCADOPAGO_ACCESS_TOKEN = os.environ.get('MERCADOPAGO_ACCESS_TOKEN', '')
MERCADOPAGO_BASE_URL = "https://api.mercadopago.com/v1"


class MercadoPagoService:
    def __init__(self):
        self.access_token = MERCADOPAGO_ACCESS_TOKEN
        self.base_url = MERCADOPAGO_BASE_URL
    
    def _get_headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json"
        }
    
    async def create_pix_payment(
        self,
        amount: float,
        description: str,
        payer_email: str,
        payer_name: str,
        payer_cpf: str,
        external_reference: str
    ) -> Dict[str, Any]:
        """Cria pagamento via PIX"""
        try:
            payload = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "pix",
                "payer": {
                    "email": payer_email,
                    "first_name": payer_name.split()[0],
                    "last_name": payer_name.split()[-1] if len(payer_name.split()) > 1 else "",
                    "identification": {
                        "type": "CPF",
                        "number": payer_cpf.replace(".", "").replace("-", "")
                    }
                },
                "external_reference": external_reference,
                "date_of_expiration": (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    # Extrair QR Code PIX
                    qr_code = None
                    qr_code_base64 = None
                    if "point_of_interaction" in data:
                        transaction_data = data["point_of_interaction"].get("transaction_data", {})
                        qr_code = transaction_data.get("qr_code")
                        qr_code_base64 = transaction_data.get("qr_code_base64")
                    
                    return {
                        "success": True,
                        "payment_id": data["id"],
                        "status": data["status"],
                        "qr_code": qr_code,
                        "qr_code_base64": qr_code_base64,
                        "expires_at": data.get("date_of_expiration")
                    }
                else:
                    logger.error(f"Mercado Pago PIX error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao criar pagamento PIX")
                    }
                    
        except Exception as e:
            logger.error(f"Mercado Pago PIX exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_boleto_payment(
        self,
        amount: float,
        description: str,
        payer_email: str,
        payer_name: str,
        payer_cpf: str,
        external_reference: str
    ) -> Dict[str, Any]:
        """Cria pagamento via Boleto"""
        try:
            payload = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "bolbradesco",
                "payer": {
                    "email": payer_email,
                    "first_name": payer_name.split()[0],
                    "last_name": payer_name.split()[-1] if len(payer_name.split()) > 1 else "",
                    "identification": {
                        "type": "CPF",
                        "number": payer_cpf.replace(".", "").replace("-", "")
                    }
                },
                "external_reference": external_reference
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    return {
                        "success": True,
                        "payment_id": data["id"],
                        "status": data["status"],
                        "barcode": data.get("barcode", {}).get("content"),
                        "boleto_url": data.get("transaction_details", {}).get("external_resource_url"),
                        "expires_at": data.get("date_of_expiration")
                    }
                else:
                    logger.error(f"Mercado Pago Boleto error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao criar boleto")
                    }
                    
        except Exception as e:
            logger.error(f"Mercado Pago Boleto exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_payment_status(self, payment_id: str) -> Dict[str, Any]:
        """Consulta status de um pagamento"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/payments/{payment_id}",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "payment_id": data["id"],
                        "status": data["status"],
                        "status_detail": data.get("status_detail"),
                        "amount": data.get("transaction_amount"),
                        "date_approved": data.get("date_approved")
                    }
                else:
                    return {"success": False, "error": "Pagamento não encontrado"}
                    
        except Exception as e:
            logger.error(f"Mercado Pago status exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_card_payment(
        self,
        amount: float,
        description: str,
        payer_email: str,
        payer_name: str,
        payer_cpf: str,
        card_number: str,
        card_expiry: str,
        card_cvv: str,
        card_holder: str,
        external_reference: str,
        installments: int = 1
    ) -> Dict[str, Any]:
        """Cria pagamento via Cartão de Crédito"""
        try:
            # Separar mês/ano do vencimento
            expiry_parts = card_expiry.replace("/", "").replace("-", "")
            expiry_month = int(expiry_parts[:2])
            expiry_year = int(f"20{expiry_parts[2:4]}" if len(expiry_parts) == 4 else expiry_parts[2:])
            
            payload = {
                "transaction_amount": amount,
                "description": description,
                "payment_method_id": "master",  # Será detectado automaticamente
                "installments": installments,
                "payer": {
                    "email": payer_email,
                    "first_name": payer_name.split()[0],
                    "last_name": payer_name.split()[-1] if len(payer_name.split()) > 1 else "",
                    "identification": {
                        "type": "CPF",
                        "number": payer_cpf.replace(".", "").replace("-", "")
                    }
                },
                "card": {
                    "card_number": card_number.replace(" ", "").replace("-", ""),
                    "expiration_month": expiry_month,
                    "expiration_year": expiry_year,
                    "security_code": card_cvv,
                    "cardholder": {
                        "name": card_holder or payer_name,
                        "identification": {
                            "type": "CPF",
                            "number": payer_cpf.replace(".", "").replace("-", "")
                        }
                    }
                },
                "external_reference": external_reference
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/payments",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    return {
                        "success": True,
                        "payment_id": str(data["id"]),
                        "status": data["status"],
                        "status_detail": data.get("status_detail"),
                        "authorization_code": data.get("authorization_code"),
                        "card_last_four": data.get("card", {}).get("last_four_digits")
                    }
                else:
                    error_data = response.json()
                    logger.error(f"Mercado Pago Card error: {response.status_code} - {error_data}")
                    return {
                        "success": False,
                        "error": error_data.get("message", "Erro ao processar cartão")
                    }
                    
        except Exception as e:
            logger.error(f"Mercado Pago Card exception: {str(e)}")
            return {"success": False, "error": str(e)}


    # ============================================
    # MÉTODOS PARA ASSINATURAS RECORRENTES
    # ============================================
    
    async def create_preapproval_plan(
        self,
        plan_id: str,
        reason: str,
        amount: float,
        currency: str = "BRL",
        frequency: int = 1,
        frequency_type: str = "months"
    ) -> Dict[str, Any]:
        """
        Cria um plano de assinatura no Mercado Pago.
        Este plano pode ser usado para criar assinaturas recorrentes.
        """
        try:
            payload = {
                "reason": reason,
                "auto_recurring": {
                    "frequency": frequency,
                    "frequency_type": frequency_type,
                    "transaction_amount": amount,
                    "currency_id": currency
                },
                "back_url": "",
                "external_reference": plan_id
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mercadopago.com/preapproval_plan",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return {
                        "success": True,
                        "plan_id": data.get("id"),
                        "init_point": data.get("init_point"),
                        "sandbox_init_point": data.get("sandbox_init_point")
                    }
                else:
                    logger.error(f"MP Create Plan error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao criar plano")
                    }
                    
        except Exception as e:
            logger.error(f"MP Create Plan exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_subscription(
        self,
        payer_email: str,
        reason: str,
        amount: float,
        back_url: str,
        external_reference: str,
        currency: str = "BRL",
        frequency: int = 1,
        frequency_type: str = "months"
    ) -> Dict[str, Any]:
        """
        Cria uma assinatura direta (preapproval) no Mercado Pago.
        Retorna URL de checkout para o usuário completar o pagamento.
        """
        try:
            payload = {
                "reason": reason,
                "external_reference": external_reference,
                "payer_email": payer_email,
                "auto_recurring": {
                    "frequency": frequency,
                    "frequency_type": frequency_type,
                    "transaction_amount": amount,
                    "currency_id": currency
                },
                "back_url": back_url,
                "status": "pending"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mercadopago.com/preapproval",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return {
                        "success": True,
                        "subscription_id": data.get("id"),
                        "init_point": data.get("init_point"),
                        "sandbox_init_point": data.get("sandbox_init_point"),
                        "status": data.get("status"),
                        "payer_id": data.get("payer_id")
                    }
                else:
                    logger.error(f"MP Create Subscription error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao criar assinatura")
                    }
                    
        except Exception as e:
            logger.error(f"MP Create Subscription exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_subscription_with_card_token(
        self,
        payer_email: str,
        card_token: str,
        reason: str,
        amount: float,
        back_url: str,
        external_reference: str,
        currency: str = "BRL",
        frequency: int = 1,
        frequency_type: str = "months"
    ) -> Dict[str, Any]:
        """
        Cria uma assinatura com cartão já tokenizado.
        O card_token deve ser gerado no frontend usando o SDK do Mercado Pago.
        """
        try:
            payload = {
                "reason": reason,
                "external_reference": external_reference,
                "payer_email": payer_email,
                "card_token_id": card_token,
                "auto_recurring": {
                    "frequency": frequency,
                    "frequency_type": frequency_type,
                    "transaction_amount": amount,
                    "currency_id": currency
                },
                "back_url": back_url,
                "status": "authorized"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.mercadopago.com/preapproval",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    return {
                        "success": True,
                        "subscription_id": data.get("id"),
                        "status": data.get("status"),
                        "next_payment_date": data.get("next_payment_date"),
                        "payer_id": data.get("payer_id")
                    }
                else:
                    logger.error(f"MP Subscription with token error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao criar assinatura")
                    }
                    
        except Exception as e:
            logger.error(f"MP Subscription with token exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def get_subscription_status(self, subscription_id: str) -> Dict[str, Any]:
        """Consulta status de uma assinatura"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"https://api.mercadopago.com/preapproval/{subscription_id}",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "subscription_id": data.get("id"),
                        "status": data.get("status"),
                        "reason": data.get("reason"),
                        "payer_email": data.get("payer_email"),
                        "next_payment_date": data.get("next_payment_date"),
                        "last_modified": data.get("last_modified"),
                        "date_created": data.get("date_created")
                    }
                else:
                    return {"success": False, "error": "Assinatura não encontrada"}
                    
        except Exception as e:
            logger.error(f"MP Get Subscription exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def cancel_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Cancela uma assinatura"""
        try:
            payload = {"status": "cancelled"}
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"https://api.mercadopago.com/preapproval/{subscription_id}",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Assinatura cancelada com sucesso"
                    }
                else:
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao cancelar assinatura")
                    }
                    
        except Exception as e:
            logger.error(f"MP Cancel Subscription exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def pause_subscription(self, subscription_id: str) -> Dict[str, Any]:
        """Pausa uma assinatura"""
        try:
            payload = {"status": "paused"}
            
            async with httpx.AsyncClient() as client:
                response = await client.put(
                    f"https://api.mercadopago.com/preapproval/{subscription_id}",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    return {
                        "success": True,
                        "message": "Assinatura pausada com sucesso"
                    }
                else:
                    return {
                        "success": False,
                        "error": response.json().get("message", "Erro ao pausar assinatura")
                    }
                    
        except Exception as e:
            logger.error(f"MP Pause Subscription exception: {str(e)}")
            return {"success": False, "error": str(e)}


# Instância singleton
mercadopago_service = MercadoPagoService()

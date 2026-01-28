"""
Serviço de PagSeguro
"""
import httpx
import base64
import os
import logging
from typing import Dict, Any
from datetime import datetime, timedelta, timezone

logger = logging.getLogger(__name__)

PAGSEGURO_EMAIL = os.environ.get('PAGSEGURO_EMAIL', '')
PAGSEGURO_TOKEN = os.environ.get('PAGSEGURO_TOKEN', '')
PAGSEGURO_BASE_URL = os.environ.get('PAGSEGURO_BASE_URL', 'https://api.pagseguro.com')


class PagSeguroService:
    def __init__(self):
        self.email = PAGSEGURO_EMAIL
        self.token = PAGSEGURO_TOKEN
        self.base_url = PAGSEGURO_BASE_URL
    
    def _get_headers(self) -> Dict[str, str]:
        credentials = f"{self.email}:{self.token}"
        encoded = base64.b64encode(credentials.encode()).decode()
        return {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json"
        }
    
    async def create_pix_payment(
        self,
        amount: float,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_cpf: str,
        reference_id: str
    ) -> Dict[str, Any]:
        """Cria pagamento via PIX no PagSeguro"""
        try:
            payload = {
                "reference_id": reference_id,
                "description": description,
                "amount": {
                    "value": int(amount * 100),  # Centavos
                    "currency": "BRL"
                },
                "payment_method": {
                    "type": "PIX"
                },
                "notification_urls": [
                    os.environ.get('WEBHOOK_URL', '') + "/api/pagamentos/webhook/pagseguro"
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    # Extrair dados do QR Code PIX
                    qr_codes = data.get("qr_codes", [])
                    qr_code = qr_codes[0].get("text") if qr_codes else None
                    qr_code_image = qr_codes[0].get("links", [{}])[0].get("href") if qr_codes else None
                    
                    return {
                        "success": True,
                        "charge_id": data["id"],
                        "status": data["status"],
                        "qr_code": qr_code,
                        "qr_code_image": qr_code_image,
                        "expires_at": data.get("created_at")
                    }
                else:
                    logger.error(f"PagSeguro PIX error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": "Erro ao criar pagamento PIX"
                    }
                    
        except Exception as e:
            logger.error(f"PagSeguro PIX exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def create_boleto_payment(
        self,
        amount: float,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_cpf: str,
        reference_id: str,
        due_date: str = None
    ) -> Dict[str, Any]:
        """Cria pagamento via Boleto no PagSeguro"""
        try:
            if not due_date:
                due_date = (datetime.now(timezone.utc) + timedelta(days=7)).strftime("%Y-%m-%d")
            
            payload = {
                "reference_id": reference_id,
                "description": description,
                "amount": {
                    "value": int(amount * 100),
                    "currency": "BRL"
                },
                "payment_method": {
                    "type": "BOLETO",
                    "boleto": {
                        "due_date": due_date,
                        "instruction_lines": {
                            "line_1": "Pagamento referente a assinatura Gestor Cred",
                            "line_2": f"Referência: {reference_id}"
                        },
                        "holder": {
                            "name": customer_name,
                            "tax_id": customer_cpf.replace(".", "").replace("-", ""),
                            "email": customer_email
                        }
                    }
                },
                "notification_urls": [
                    os.environ.get('WEBHOOK_URL', '') + "/api/pagamentos/webhook/pagseguro"
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    # Extrair dados do boleto
                    boleto_data = data.get("payment_method", {}).get("boleto", {})
                    
                    return {
                        "success": True,
                        "charge_id": data["id"],
                        "status": data["status"],
                        "barcode": boleto_data.get("barcode"),
                        "formatted_barcode": boleto_data.get("formatted_barcode"),
                        "due_date": boleto_data.get("due_date"),
                        "pdf_url": None  # PagSeguro retorna em links
                    }
                else:
                    logger.error(f"PagSeguro Boleto error: {response.status_code} - {response.text}")
                    return {
                        "success": False,
                        "error": "Erro ao criar boleto"
                    }
                    
        except Exception as e:
            logger.error(f"PagSeguro Boleto exception: {str(e)}")
            return {"success": False, "error": str(e)}
    
    async def get_charge_status(self, charge_id: str) -> Dict[str, Any]:
        """Consulta status de uma cobrança"""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/charges/{charge_id}",
                    headers=self._get_headers(),
                    timeout=10.0
                )
                
                if response.status_code == 200:
                    data = response.json()
                    return {
                        "success": True,
                        "charge_id": data["id"],
                        "status": data["status"],
                        "amount": data.get("amount", {}).get("value", 0) / 100,
                        "paid_at": data.get("paid_at")
                    }
                else:
                    return {"success": False, "error": "Cobrança não encontrada"}
                    
        except Exception as e:
            logger.error(f"PagSeguro status exception: {str(e)}")
            return {"success": False, "error": str(e)}

    async def create_card_payment(
        self,
        amount: float,
        description: str,
        customer_name: str,
        customer_email: str,
        customer_cpf: str,
        card_number: str,
        card_expiry: str,
        card_cvv: str,
        card_holder: str,
        reference_id: str,
        installments: int = 1
    ) -> Dict[str, Any]:
        """Cria pagamento via Cartão de Crédito no PagSeguro"""
        try:
            # Separar mês/ano do vencimento
            expiry_parts = card_expiry.replace("/", "").replace("-", "")
            expiry_month = expiry_parts[:2]
            expiry_year = f"20{expiry_parts[2:4]}" if len(expiry_parts) == 4 else expiry_parts[2:]
            
            payload = {
                "reference_id": reference_id,
                "description": description,
                "amount": {
                    "value": int(amount * 100),
                    "currency": "BRL"
                },
                "payment_method": {
                    "type": "CREDIT_CARD",
                    "installments": installments,
                    "capture": True,
                    "card": {
                        "number": card_number.replace(" ", "").replace("-", ""),
                        "exp_month": expiry_month,
                        "exp_year": expiry_year,
                        "security_code": card_cvv,
                        "holder": {
                            "name": card_holder or customer_name
                        }
                    }
                },
                "customer": {
                    "name": customer_name,
                    "email": customer_email,
                    "tax_id": customer_cpf.replace(".", "").replace("-", "")
                },
                "notification_urls": [
                    os.environ.get('WEBHOOK_URL', '') + "/api/checkout/webhook/pagseguro"
                ]
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/charges",
                    json=payload,
                    headers=self._get_headers(),
                    timeout=30.0
                )
                
                if response.status_code in (200, 201):
                    data = response.json()
                    
                    return {
                        "success": True,
                        "charge_id": data["id"],
                        "status": data["status"],
                        "authorization_code": data.get("payment_response", {}).get("code"),
                        "card_last_four": card_number[-4:]
                    }
                else:
                    error_data = response.json()
                    logger.error(f"PagSeguro Card error: {response.status_code} - {error_data}")
                    return {
                        "success": False,
                        "error": "Erro ao processar cartão"
                    }
                    
        except Exception as e:
            logger.error(f"PagSeguro Card exception: {str(e)}")
            return {"success": False, "error": str(e)}


# Instância singleton
pagseguro_service = PagSeguroService()

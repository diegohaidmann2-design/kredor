"""
Modelos de Configuração do Asaas
"""
from pydantic import BaseModel
from typing import Optional


class AsaasConfig(BaseModel):
    """Configuração do Asaas armazenada no banco"""
    habilitado: bool = False
    api_key: str = ""
    ambiente: str = "sandbox"  # sandbox ou producao
    webhook_url: str = ""


class AsaasCustomer(BaseModel):
    """Cliente criado no Asaas"""
    id: str
    name: str
    email: str
    cpfCnpj: str
    mobilePhone: Optional[str] = None


class AsaasPayment(BaseModel):
    """Cobrança no Asaas"""
    id: str
    customer: str
    billingType: str  # PIX, BOLETO, CREDIT_CARD, UNDEFINED
    value: float
    dueDate: str
    status: str  # PENDING, CONFIRMED, RECEIVED, OVERDUE
    description: Optional[str] = None
    externalReference: Optional[str] = None


class AsaasSubscription(BaseModel):
    """Assinatura recorrente no Asaas"""
    id: str
    customer: str
    billingType: str
    value: float
    nextDueDate: str
    cycle: str  # MONTHLY, YEARLY, etc
    status: str  # ACTIVE, EXPIRED, CANCELED
    description: Optional[str] = None

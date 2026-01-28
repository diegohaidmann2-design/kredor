"""
Modelo de Configurações
"""
from pydantic import BaseModel
from typing import Optional, List, Literal


class PlanoConfig(BaseModel):
    nome: str
    preco: str
    recursos: List[str]
    destaque: bool = False


class LandingConfig(BaseModel):
    nome_empresa: str = "Gestor Cred"
    slogan: str = "Sistema de Gestão de Empréstimos a Juros"
    descricao: str = "Gerencie seus empréstimos de forma simples e profissional"
    whatsapp: str = ""
    whatsapp_numero: str = ""
    whatsapp_mensagem: str = "Olá! Gostaria de saber mais sobre o Gestor Cred."
    cor_primaria: str = "#1e40af"
    plano_trial_dias: int = 7
    plano_basico_preco: float = 97.0
    plano_basico_clientes: int = 50
    plano_basico_emprestimos: int = 100
    plano_profissional_preco: float = 197.0
    plano_profissional_clientes: int = 200
    plano_profissional_emprestimos: int = 500
    plano_enterprise_preco: float = 497.0
    plano_enterprise_clientes: int = -1
    plano_enterprise_emprestimos: int = -1
    planos: Optional[List[PlanoConfig]] = None


class GatewayConfig(BaseModel):
    """Configuração de um gateway de pagamento"""
    habilitado: bool = False
    # Mercado Pago
    mercadopago_access_token: str = ""
    mercadopago_public_key: str = ""
    # PagSeguro
    pagseguro_email: str = ""
    pagseguro_token: str = ""
    # Modo de operação: mercadopago, pagseguro, rotacao
    modo_gateway: Literal["mercadopago", "pagseguro", "rotacao"] = "mercadopago"
    # Métodos habilitados
    pix_habilitado: bool = True
    cartao_habilitado: bool = True
    # Rotação - contador para alternar entre gateways
    rotacao_contador: int = 0


class AssinaturaGatewayConfig(BaseModel):
    """Configuração de gateways para assinaturas recorrentes"""
    # Estratégia: stripe_only, mercadopago_only, rotacao, fallback
    estrategia: Literal["stripe_only", "mercadopago_only", "rotacao", "fallback"] = "stripe_only"
    
    # Stripe
    stripe_habilitado: bool = True
    stripe_api_key: str = ""  # Secret Key - Será carregado do .env se vazio
    stripe_publishable_key: str = ""  # Publishable Key
    stripe_modo_sandbox: bool = True
    stripe_webhook_secret: str = ""
    stripe_webhook_url: str = ""
    
    # Mercado Pago
    mercadopago_habilitado: bool = False
    mercadopago_access_token: str = ""
    mercadopago_public_key: str = ""
    mercadopago_modo_sandbox: bool = True
    mercadopago_webhook_secret: str = ""
    mercadopago_webhook_url: str = ""
    
    # Métodos habilitados no Mercado Pago
    mp_cartao_habilitado: bool = True
    mp_pix_habilitado: bool = True
    
    # Contador para rotação
    rotacao_contador: int = 0
    
    # Gateway preferido para fallback (qual tentar primeiro)
    gateway_primario: Literal["stripe", "mercadopago"] = "stripe"


class IAConfig(BaseModel):
    """Configuração do Assistente IA"""
    habilitado: bool = True
    provider: Literal["gemini", "openai"] = "gemini"
    api_key: str = ""  # Será carregado do .env se vazio
    modelo: str = "gemini-1.5-flash"
    temperatura: float = 0.7


"""
Modelo de Configurações
"""
from pydantic import BaseModel
from typing import Optional, List, Literal

from config import TRIAL_DIAS


class PlanoConfig(BaseModel):
    nome: str
    preco: str
    recursos: List[str]
    destaque: bool = False


class LandingConfig(BaseModel):
    nome_empresa: str = "Kredor"
    slogan: str = "Sistema de Gestão de Empréstimos a Juros"
    descricao: str = "Gerencie seus empréstimos de forma simples e profissional"
    whatsapp: str = ""
    whatsapp_numero: str = ""
    whatsapp_mensagem: str = "Olá! Gostaria de saber mais sobre o Kredor."
    cor_primaria: str = "#1e40af"
    # Dados institucionais (exibidos no rodapé público)
    razao_social: str = ""
    cnpj: str = ""
    email_suporte: str = ""
    endereco: str = ""
    # Redes sociais (exibidas no rodapé público)
    social_facebook: str = ""
    social_instagram: str = ""
    social_linkedin: str = ""
    social_youtube: str = ""
    plano_trial_dias: int = TRIAL_DIAS
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


# GatewayConfig (legado, com MercadoPago/PagSeguro) removido — gateways oficiais: Asaas + SyncPay.


class AssinaturaGatewayConfig(BaseModel):
    """
    Configuração de gateways para assinaturas recorrentes
    Suporta: Asaas (PIX/Boleto/Cartão) + SyncPay (PIX instantâneo)
    """
    # Estratégia: asaas_only, syncpay_only, rotacao, fallback
    estrategia: Literal["asaas_only", "syncpay_only", "rotacao", "fallback"] = "asaas_only"
    
    # Asaas (Gateway Brasileiro - Full)
    asaas_habilitado: bool = True
    asaas_api_key: str = ""
    asaas_ambiente: Literal["sandbox", "producao"] = "sandbox"
    asaas_webhook_url: str = ""
    asaas_webhook_token: str = ""
    
    # SyncPay (PIX instantâneo - Novo)
    syncpay_habilitado: bool = False
    syncpay_client_id: str = ""
    syncpay_client_secret: str = ""
    syncpay_ambiente: Literal["sandbox", "producao"] = "sandbox"
    syncpay_webhook_url: str = ""
    syncpay_webhook_secret: str = ""
    
    # Contador para rotação
    rotacao_contador: int = 0
    
    # Gateway preferido para fallback
    gateway_primario: Literal["asaas", "syncpay"] = "asaas"


class IAConfig(BaseModel):
    """Configuração do Assistente IA"""
    habilitado: bool = True
    provider: Literal["gemini", "openai"] = "gemini"
    api_key: str = ""  # Será carregado do .env se vazio
    modelo: str = "gemini-1.5-flash"
    temperatura: float = 0.7


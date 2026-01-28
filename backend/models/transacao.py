"""
Modelo de Transação de Checkout
Armazena todas as tentativas de pagamento (sucesso ou falha)
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from enum import Enum

class StatusTransacao(str, Enum):
    """Status possíveis de uma transação"""
    PENDENTE = "pendente"
    PROCESSANDO = "processando"
    APROVADO = "aprovado"
    RECUSADO = "recusado"
    EXPIRADO = "expirado"
    CANCELADO = "cancelado"
    ERRO = "erro"

class MetodoPagamento(str, Enum):
    """Métodos de pagamento disponíveis"""
    PIX = "pix"
    CARTAO_CREDITO = "cartao_credito"
    BOLETO = "boleto"

class MotivoRecusa(str, Enum):
    """Motivos comuns de recusa"""
    SALDO_INSUFICIENTE = "saldo_insuficiente"
    LIMITE_EXCEDIDO = "limite_excedido"
    CARTAO_INVALIDO = "cartao_invalido"
    CARTAO_EXPIRADO = "cartao_expirado"
    DADOS_INCORRETOS = "dados_incorretos"
    SUSPEITA_FRAUDE = "suspeita_fraude"
    TEMPO_EXPIRADO = "tempo_expirado"
    ERRO_GATEWAY = "erro_gateway"
    OUTRO = "outro"

class TransacaoCheckout(BaseModel):
    """Modelo de transação de checkout"""
    id: str
    usuario_id: Optional[str] = None
    usuario_email: str
    usuario_nome: str
    usuario_cpf: Optional[str] = None
    usuario_telefone: Optional[str] = None
    
    # Dados do plano
    plano_id: str
    plano_nome: str
    valor: float
    
    # Dados de pagamento
    metodo_pagamento: MetodoPagamento
    status: StatusTransacao
    
    # IDs externos
    payment_id: Optional[str] = None
    order_id: Optional[str] = None
    
    # Dados específicos do método
    dados_pagamento: Dict[str, Any] = {}  # QR Code, dados cartão, etc
    
    # Controle de falhas
    motivo_recusa: Optional[MotivoRecusa] = None
    mensagem_erro: Optional[str] = None
    tentativas: int = 1
    
    # Remarketing
    email_enviado: bool = False
    cupom_gerado: Optional[str] = None
    data_email: Optional[datetime] = None
    
    # Timestamps
    criado_em: datetime
    atualizado_em: datetime
    expira_em: Optional[datetime] = None
    
    # Metadados
    ip_origem: Optional[str] = None
    user_agent: Optional[str] = None
    

class FiltrosTransacao(BaseModel):
    """Filtros para busca de transações"""
    status: Optional[StatusTransacao] = None
    metodo_pagamento: Optional[MetodoPagamento] = None
    data_inicio: Optional[datetime] = None
    data_fim: Optional[datetime] = None
    usuario_email: Optional[str] = None
    plano_id: Optional[str] = None
    valor_min: Optional[float] = None
    valor_max: Optional[float] = None
    email_enviado: Optional[bool] = None
    skip: int = 0
    limit: int = 50

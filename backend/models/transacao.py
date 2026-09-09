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

"""
Modelo de Empréstimo e Parcelas
"""
from pydantic import BaseModel, Field
from typing import Optional, Literal, List
from datetime import datetime, timezone
import uuid


class Parcela(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    emprestimo_id: str
    numero_parcela: int
    data_vencimento: datetime
    valor_principal: float
    valor_juros: float
    valor_total: float
    valor_pago: float = 0.0
    valor_multa: float = 0.0
    valor_juros_mora: float = 0.0
    dias_atraso: int = 0
    saldo_devedor: float
    status: Literal["pendente", "pago", "atrasado", "parcial"] = "pendente"
    data_pagamento: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParcelaSimulacao(BaseModel):
    numero_parcela: int
    data_vencimento: str
    valor_principal: float
    valor_juros: float
    valor_total: float
    saldo_devedor: float


class Emprestimo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str
    valor_principal: float
    taxa_juros_mensal: float
    prazo_meses: int
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    data_inicio: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valor_total_com_juros: float = 0.0
    valor_total_juros: float = 0.0
    status: Literal["ativo", "quitado", "inadimplente", "cancelado"] = "ativo"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmprestimoCreate(BaseModel):
    cliente_id: str
    valor_principal: float
    taxa_juros_mensal: float
    prazo_meses: int
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    data_inicio: Optional[datetime] = None


class SimulacaoRequest(BaseModel):
    valor_principal: float
    taxa_juros_mensal: float
    prazo_meses: int
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033


class SimulacaoResponse(BaseModel):
    valor_principal: float
    taxa_juros_mensal: float
    prazo_meses: int
    metodo_calculo: str
    periodo_carencia_meses: int
    valor_total_com_juros: float
    valor_total_juros: float
    parcelas: List[ParcelaSimulacao]

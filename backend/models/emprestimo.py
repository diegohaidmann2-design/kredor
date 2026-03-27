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
    total_parcelas: Optional[int] = None
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
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    periodicidade: Literal["mensal", "semanal"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    data_inicio: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    valor_total_com_juros: float = 0.0
    valor_total_juros: float = 0.0
    status: Literal["ativo", "quitado", "inadimplente", "cancelado"] = "ativo"
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmprestimoCreate(BaseModel):
    cliente_id: str
    valor_principal: float
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    periodicidade: Literal["mensal", "semanal"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    data_inicio: Optional[datetime] = None
    dia_vencimento: Optional[int] = None


class EmprestimoUpdate(BaseModel):
    cliente_id: Optional[str] = None
    valor_principal: Optional[float] = None
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: Optional[Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]] = None
    periodo_carencia_meses: Optional[int] = None
    taxa_multa_atraso: Optional[float] = None
    taxa_juros_mora_diario: Optional[float] = None
    data_inicio: Optional[datetime] = None
    status: Optional[Literal["ativo", "quitado", "inadimplente", "cancelado"]] = None


class SimulacaoRequest(BaseModel):
    valor_principal: float
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    periodicidade: Literal["mensal", "semanal"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    dia_vencimento: Optional[int] = None


class SimulacaoResponse(BaseModel):
    valor_principal: float
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: str
    periodo_carencia_meses: int
    periodicidade: str
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    valor_total_com_juros: float
    valor_total_juros: float
    parcelas: List[ParcelaSimulacao]

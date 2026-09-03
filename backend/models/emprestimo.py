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
    valor_principal: float = 0.0
    valor_juros: float = 0.0
    valor_total: float
    valor_pago: float = 0.0
    valor_multa: float = 0.0
    valor_juros_mora: float = 0.0
    dias_atraso: int = 0
    saldo_devedor: float = 0.0
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
    sem_prazo: bool = False  # Empréstimo aberto (geração automática de parcelas)
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
    sem_prazo: bool = False  # Empréstimo aberto
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
    periodicidade: Optional[Literal["mensal", "semanal"]] = None
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    sem_prazo: Optional[bool] = None
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
    periodicidade: Literal["mensal", "semanal", "diario"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    taxa_juros_diaria: Optional[float] = None
    prazo_dias: Optional[int] = None
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
    taxa_juros_diaria: Optional[float] = None
    prazo_dias: Optional[int] = None
    valor_total_com_juros: float
    valor_total_juros: float
    parcelas: List[ParcelaSimulacao]


class AmortizacaoRequest(BaseModel):
    """Request para amortizar capital de empréstimo aberto (sem prazo)"""
    valor_amortizacao: float = Field(..., gt=0, description="Valor pago para abater capital")
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"] = "pix"
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
    recalcular_juros: bool = False  # Se True, recalcula juros das proximas parcelas pendentes


class ProrrogacaoRequest(BaseModel):
    """Request para prorrogar empréstimo"""
    periodos: int = Field(..., gt=0, description="Quantidade de períodos (meses ou semanas) para prorrogar")


class ProrrogacaoResponse(BaseModel):
    """Response da prorrogação"""
    mensagem: str
    emprestimo_id: str
    periodos_adicionados: int
    novo_total_parcelas: int
    novas_parcelas_criadas: List[dict]

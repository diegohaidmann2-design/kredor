"""
Modelo de Empréstimo e Parcelas
"""
from pydantic import BaseModel, Field
from utils.dinheiro import EntradaEmReais
from typing import Optional, Literal, List
from datetime import datetime, timezone
import uuid


class Parcela(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    emprestimo_id: str
    numero_parcela: int
    data_vencimento: datetime
    valor_principal_centavos: int = 0
    valor_juros_centavos: int = 0
    valor_total_centavos: int
    valor_pago_centavos: int = 0
    valor_multa_centavos: int = 0
    valor_juros_mora_centavos: int = 0
    dias_atraso: int = 0
    saldo_devedor_centavos: int = 0
    total_parcelas: Optional[int] = None
    status: Literal["pendente", "pago", "atrasado", "parcial"] = "pendente"
    data_pagamento: Optional[datetime] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ParcelaSimulacao(BaseModel):
    numero_parcela: int
    data_vencimento: str
    valor_principal_centavos: int
    valor_juros_centavos: int
    valor_total_centavos: int
    saldo_devedor_centavos: int


class Emprestimo(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    cliente_id: str
    valor_principal_centavos: int
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
    valor_total_com_juros_centavos: int = 0
    valor_total_juros_centavos: int = 0
    status: Literal["ativo", "quitado", "inadimplente", "cancelado"] = "ativo"
    aceite: Optional[dict] = None
    historico_prorrogacoes: List[dict] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EmprestimoCreate(EntradaEmReais):
    cliente_id: str
    valor_principal_centavos: int = Field(..., ge=1, le=1_000_000_000_00)  # até R$ 1 bi
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = Field(None, ge=1, le=600)  # 50 anos
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    periodicidade: Literal["mensal", "semanal"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = Field(None, ge=1, le=2_600)  # 50 anos
    sem_prazo: bool = False  # Empréstimo aberto
    data_inicio: Optional[datetime] = None
    dia_vencimento: Optional[int] = None


class EmprestimoUpdate(EntradaEmReais):
    cliente_id: Optional[str] = None
    valor_principal_centavos: Optional[int] = None
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


class SimulacaoRequest(EntradaEmReais):
    valor_principal_centavos: int = Field(..., ge=1, le=1_000_000_000_00)  # até R$ 1 bi
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = Field(None, ge=1, le=600)  # 50 anos
    metodo_calculo: Literal["juros_simples", "juros_compostos", "tabela_price", "sac", "apenas_juros"]
    periodo_carencia_meses: int = 0
    taxa_multa_atraso: float = 2.0
    taxa_juros_mora_diario: float = 0.033
    periodicidade: Literal["mensal", "semanal", "diario"] = "mensal"
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = Field(None, ge=1, le=2_600)  # 50 anos
    taxa_juros_diaria: Optional[float] = None
    prazo_dias: Optional[int] = Field(None, ge=1, le=18_250)  # 50 anos
    dia_vencimento: Optional[int] = None
    data_inicio: Optional[datetime] = None


class SimulacaoResponse(BaseModel):
    valor_principal_centavos: int
    taxa_juros_mensal: Optional[float] = None
    prazo_meses: Optional[int] = None
    metodo_calculo: str
    periodo_carencia_meses: int
    periodicidade: str
    taxa_juros_semanal: Optional[float] = None
    prazo_semanas: Optional[int] = None
    taxa_juros_diaria: Optional[float] = None
    prazo_dias: Optional[int] = None
    valor_total_com_juros_centavos: int
    valor_total_juros_centavos: int
    parcelas: List[ParcelaSimulacao]


class AmortizacaoRequest(EntradaEmReais):
    """Request para amortizar capital de empréstimo aberto (sem prazo)"""
    valor_amortizacao_centavos: int = Field(..., gt=0, description="Valor pago para abater capital (centavos)")
    metodo_pagamento: Literal["dinheiro", "pix", "transferencia", "boleto", "cartao"] = "pix"
    data_pagamento: Optional[datetime] = None
    observacoes: Optional[str] = None
    recalcular_juros: bool = False  # Se True, recalcula juros das proximas parcelas pendentes


class IncorporacaoJurosRequest(EntradaEmReais):
    """Request para incorporar juros (não pagos) ao capital de um empréstimo aberto (sem prazo).

    Operação MANUAL: o usuário informa quanto de juros deseja somar ao capital.
    Não é um recebimento — apenas converte juros em capital (novo_principal += valor).
    """
    valor_juros_centavos: int = Field(..., gt=0, description="Valor de juros a incorporar ao capital (centavos)")
    baixar_parcelas: bool = True  # Baixa as parcelas de juros em aberto correspondentes
    recalcular_juros: bool = False  # Recalcula juros das próximas parcelas com o novo capital
    data_incorporacao: Optional[datetime] = None
    observacoes: Optional[str] = None


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

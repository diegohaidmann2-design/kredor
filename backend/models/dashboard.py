"""
Modelo de Dashboard
"""
from pydantic import BaseModel
from typing import List, Optional


class DashboardStats(BaseModel):
    total_capital_emprestado: float
    total_juros_a_receber: float
    total_juros_recebidos: float
    taxa_inadimplencia: float
    total_clientes_ativos: int
    total_emprestimos_ativos: int
    total_parcelas_atrasadas: int = 0
    total_clientes_em_atraso: int = 0
    proximos_vencimentos: List[dict]
    # Dados para gráficos
    evolucao_mensal: Optional[List[dict]] = []
    distribuicao_status: Optional[List[dict]] = []
    top_clientes: Optional[List[dict]] = []
    metodos_calculo: Optional[List[dict]] = []

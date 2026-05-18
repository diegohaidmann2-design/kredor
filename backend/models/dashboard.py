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

    # ===== NOVOS CAMPOS - FOCO EM PAGAMENTOS PENDENTES =====
    # Valor monetário em atraso (saldo + multa + juros mora)
    valor_em_atraso: float = 0.0
    # A receber hoje / 7 dias / mês
    a_receber_hoje: float = 0.0
    a_receber_semana: float = 0.0
    a_receber_mes: float = 0.0
    # Recebido no mês atual (capital + juros) - real, não mais 30% chutado
    recebido_mes_atual: float = 0.0
    # Próxima parcela a vencer
    proximo_recebimento: Optional[dict] = None
    # Aging dos atrasos (faixas de dias)
    aging_atrasos: List[dict] = []
    # Top inadimplentes (cliente_id, nome, valor_devido, dias_max_atraso, parcelas_atrasadas, telefone)
    top_inadimplentes: List[dict] = []

    # Dados para gráficos
    evolucao_mensal: Optional[List[dict]] = []
    distribuicao_status: Optional[List[dict]] = []
    top_clientes: Optional[List[dict]] = []
    metodos_calculo: Optional[List[dict]] = []

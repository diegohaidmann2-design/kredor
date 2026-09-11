"""
Modelo de Dashboard
"""
from pydantic import BaseModel
from typing import List, Optional


class DashboardStats(BaseModel):
    total_capital_emprestado_centavos: int
    total_juros_a_receber_centavos: int
    total_juros_recebidos_centavos: int
    taxa_inadimplencia: float
    total_clientes_ativos: int
    total_emprestimos_ativos: int
    total_parcelas_atrasadas: int = 0
    total_clientes_em_atraso: int = 0
    proximos_vencimentos: List[dict]

    # ===== NOVOS CAMPOS - FOCO EM PAGAMENTOS PENDENTES =====
    # Valor monetário em atraso (saldo + multa + juros mora)
    valor_em_atraso_centavos: int = 0
    # A receber hoje / 7 dias / mês
    a_receber_hoje_centavos: int = 0
    a_receber_semana_centavos: int = 0
    a_receber_mes_centavos: int = 0
    # Recebido no mês atual (capital + juros) - real, não mais 30% chutado
    recebido_mes_atual_centavos: int = 0
    # Juros do mês: recebidos (parte de juros dos pagamentos do mês) e a receber (parcelas que
    # ainda vencem de hoje ao fim do mês; as já vencidas estão em valor_em_atraso)
    juros_recebidos_mes_centavos: int = 0
    juros_a_receber_mes_centavos: int = 0
    # Tudo o que ainda vai entrar: capital em aberto + juros + multa/mora não pagos
    total_a_receber_centavos: int = 0
    encargos_a_receber_centavos: int = 0
    # Próxima parcela a vencer
    proximo_recebimento: Optional[dict] = None
    # Aging dos atrasos (faixas de dias)
    aging_atrasos: List[dict] = []
    # Top inadimplentes (cliente_id, nome, valor_devido, dias_max_atraso, parcelas_atrasadas, telefone)
    top_inadimplentes: List[dict] = []

    # Dados para gráficos
    evolucao_mensal: Optional[List[dict]] = []
    # Ganhos com juros mês a mês (juros + multa + mora recebidos)
    evolucao_ganhos_mensal: Optional[List[dict]] = []
    distribuicao_status: Optional[List[dict]] = []
    top_clientes: Optional[List[dict]] = []
    metodos_calculo: Optional[List[dict]] = []

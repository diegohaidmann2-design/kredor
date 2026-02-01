"""
Rotas do Dashboard - Versão com Gráficos
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from config import db
from models.dashboard import DashboardStats
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo
from services.soft_delete_service import SoftDeleteService

router = APIRouter()


@router.get("", response_model=DashboardStats)
async def get_dashboard(current_user: Usuario = Depends(verificar_plano_ativo)):
    """Retorna estatísticas do dashboard com dados para gráficos"""
    user_filter = {"usuario_id": get_user_context(current_user)}
    
    # Total de capital emprestado
    query_emprestimos = SoftDeleteService.get_active_filter(
        get_user_context(current_user), 
        {"status": {"$in": ["ativo", "inadimplente"]}}
    )
    emprestimos = await db.emprestimos.find(
        query_emprestimos,
        {"_id": 0}
    ).to_list(1000)
    
    total_capital = sum(e.get("valor_principal", 0) for e in emprestimos)
    total_juros_a_receber = sum(e.get("valor_total_juros", 0) for e in emprestimos)
    
    # Juros já recebidos
    pagamentos = await db.pagamentos.find(
        SoftDeleteService.get_active_filter(get_user_context(current_user)), 
        {"_id": 0}
    ).to_list(1000)
    total_juros_recebidos = sum(p.get("valor_pago", 0) for p in pagamentos) * 0.3
    
    # Taxa de inadimplência
    query_total = SoftDeleteService.get_active_filter(get_user_context(current_user))
    total_emprestimos = await db.emprestimos.count_documents(query_total)
    
    query_inadimplentes = SoftDeleteService.get_active_filter(
        get_user_context(current_user), 
        {"status": "inadimplente"}
    )
    emprestimos_inadimplentes = await db.emprestimos.count_documents(query_inadimplentes)
    taxa_inadimplencia = (emprestimos_inadimplentes / total_emprestimos * 100) if total_emprestimos > 0 else 0
    
    # Clientes e empréstimos ativos
    query_clientes_ativos = SoftDeleteService.get_active_filter(
        get_user_context(current_user), 
        {"status": "ativo"}
    )
    total_clientes = await db.clientes.count_documents(query_clientes_ativos)
    
    query_loans_ativos = SoftDeleteService.get_active_filter(
        get_user_context(current_user), 
        {"status": "ativo"}
    )
    total_emprestimos_ativos = await db.emprestimos.count_documents(query_loans_ativos)
    
    # Próximos vencimentos (7 dias)
    hoje = datetime.now(timezone.utc)
    proximos_7_dias = hoje + timedelta(days=7)
    
    query_parcelas_proximas = SoftDeleteService.get_active_filter(get_user_context(current_user), {
        "status": {"$in": ["pendente", "parcial"]},
        "data_vencimento": {"$lte": proximos_7_dias.isoformat()}
    })
    
    parcelas = await db.parcelas.find(query_parcelas_proximas, {"_id": 0}).sort("data_vencimento", 1).limit(10).to_list(10)
    
    proximos_vencimentos = []
    for p in parcelas:
        emprestimo = await db.emprestimos.find_one(
            {"id": p["emprestimo_id"]},
            {"_id": 0, "cliente_id": 1}
        )
        if emprestimo:
            cliente = await db.clientes.find_one(
                {"id": emprestimo["cliente_id"]},
                {"_id": 0, "nome": 1}
            )
            proximos_vencimentos.append({
                "parcela_id": p["id"],
                "emprestimo_id": p["emprestimo_id"],
                "cliente_nome": cliente.get("nome", "N/A") if cliente else "N/A",
                "numero_parcela": p["numero_parcela"],
                "data_vencimento": p["data_vencimento"],
                "valor_total": p["valor_total"]
            })
    
    # ========== DADOS PARA GRÁFICOS ==========
    
    # 1. Evolução Mensal (últimos 12 meses)
    query_all = SoftDeleteService.get_active_filter(get_user_context(current_user))
    todos_emprestimos = await db.emprestimos.find(
        query_all, {"_id": 0, "created_at": 1, "valor_principal": 1}
    ).to_list(10000)
    
    evolucao_mensal = []
    for i in range(11, -1, -1):
        mes_ref = hoje - timedelta(days=30 * i)
        mes_str = mes_ref.strftime("%b/%y")
        
        valor_mes = 0
        for e in todos_emprestimos:
            created = e.get("created_at")
            if created:
                if isinstance(created, str):
                    try:
                        created = datetime.fromisoformat(created.replace("Z", "+00:00"))
                    except (ValueError, TypeError):
                        continue
                if created.year == mes_ref.year and created.month == mes_ref.month:
                    valor_mes += e.get("valor_principal", 0)
        
        evolucao_mensal.append({
            "mes": mes_str,
            "valor": round(valor_mes, 2)
        })
    
    # 2. Distribuição por Status
    status_counts = defaultdict(int)
    # 2. Distribuição por Status
    status_counts = defaultdict(int)
    all_emp = await db.emprestimos.find(query_all, {"_id": 0, "status": 1, "metodo_calculo": 1}).to_list(10000)
    for e in all_emp:
        status_counts[e.get("status", "desconhecido")] += 1
    
    distribuicao_status = [
        {"name": "Ativo", "value": status_counts.get("ativo", 0), "color": "#3b82f6"},
        {"name": "Quitado", "value": status_counts.get("quitado", 0), "color": "#22c55e"},
        {"name": "Inadimplente", "value": status_counts.get("inadimplente", 0), "color": "#ef4444"},
        {"name": "Cancelado", "value": status_counts.get("cancelado", 0), "color": "#6b7280"},
    ]
    
    # 3. Top 5 Clientes por Valor Emprestado
    cliente_valores = defaultdict(float)
    for e in emprestimos:
        cliente_valores[e.get("cliente_id", "")] += e.get("valor_principal", 0)
    
    top_clientes = []
    sorted_clientes = sorted(cliente_valores.items(), key=lambda x: x[1], reverse=True)[:5]
    for cliente_id, valor in sorted_clientes:
        cliente = await db.clientes.find_one({"id": cliente_id}, {"_id": 0, "nome": 1})
        top_clientes.append({
            "nome": cliente.get("nome", "N/A")[:20] if cliente else "N/A",
            "valor": round(valor, 2)
        })
    
    # 4. Distribuição por Método de Cálculo
    metodo_counts = defaultdict(int)
    for e in all_emp:
        metodo_counts[e.get("metodo_calculo", "simples")] += 1
    
    metodos_calculo = [
        {"name": "Juros Simples", "value": metodo_counts.get("simples", 0)},
        {"name": "Juros Compostos", "value": metodo_counts.get("composto", 0)},
        {"name": "Tabela Price", "value": metodo_counts.get("price", 0)},
        {"name": "SAC", "value": metodo_counts.get("sac", 0)},
    ]
    
    return DashboardStats(
        total_capital_emprestado=round(total_capital, 2),
        total_juros_a_receber=round(total_juros_a_receber, 2),
        total_juros_recebidos=round(total_juros_recebidos, 2),
        taxa_inadimplencia=round(taxa_inadimplencia, 2),
        total_clientes_ativos=total_clientes,
        total_emprestimos_ativos=total_emprestimos_ativos,
        proximos_vencimentos=proximos_vencimentos,
        evolucao_mensal=evolucao_mensal,
        distribuicao_status=distribuicao_status,
        top_clientes=top_clientes,
        metodos_calculo=metodos_calculo
    )

"""
Rotas do Dashboard - Versão com Gráficos + Foco em Pagamentos Pendentes
"""
from fastapi import APIRouter, Depends
from datetime import datetime, timedelta, timezone
from collections import defaultdict

from config import db
from models.dashboard import DashboardStats
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo
from services.soft_delete_service import SoftDeleteService

router = APIRouter()


def _parse_date(value):
    """Converte string ISO ou datetime em datetime tz-aware (UTC)."""
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    if isinstance(value, str):
        try:
            dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None
    return None


def _valor_devido_parcela(p: dict) -> int:
    """Calcula o valor devido real de uma parcela (saldo + multa + juros mora)."""
    return (
        (p.get("valor_total_centavos", 0) or 0)
        - (p.get("valor_pago_centavos", 0) or 0)
        + (p.get("valor_multa_centavos", 0) or 0)
        + (p.get("valor_juros_mora_centavos", 0) or 0)
    )


@router.get("", response_model=DashboardStats)
async def get_dashboard(current_user: Usuario = Depends(verificar_plano_ativo)):
    """Retorna estatísticas do dashboard com dados para gráficos"""

    context_id = get_user_context(current_user)
    hoje = datetime.now(timezone.utc)
    hoje_inicio = hoje.replace(hour=0, minute=0, second=0, microsecond=0)
    fim_hoje = hoje_inicio + timedelta(days=1)
    fim_semana = hoje_inicio + timedelta(days=7)
    inicio_mes = hoje_inicio.replace(day=1)
    if inicio_mes.month == 12:
        fim_mes = inicio_mes.replace(year=inicio_mes.year + 1, month=1)
    else:
        fim_mes = inicio_mes.replace(month=inicio_mes.month + 1)

    # ==================== EMPRÉSTIMOS ATIVOS ====================
    query_emprestimos = SoftDeleteService.get_active_filter(
        context_id,
        {"status": {"$in": ["ativo", "inadimplente"]}}
    )
    emprestimos = await db.emprestimos.find(
        query_emprestimos, {"_id": 0}
    ).to_list(10000)

    total_capital = sum(e.get("valor_principal_centavos", 0) or 0 for e in emprestimos)

    # ==================== PARCELAS PENDENTES (PENDENTE/PARCIAL/ATRASADO) ====================
    query_parcelas_pendentes = SoftDeleteService.get_active_filter(context_id, {
        "status": {"$in": ["pendente", "parcial", "atrasado"]}
    })
    parcelas_pendentes = await db.parcelas.find(
        query_parcelas_pendentes, {"_id": 0}
    ).to_list(50000)

    total_juros_a_receber = sum(p.get("valor_juros_centavos", 0) or 0 for p in parcelas_pendentes)

    # ==================== PARCELAS PAGAS - JUROS RECEBIDOS REAL ====================
    # Bug fix: agora soma valor_juros_centavos real das parcelas pagas, não 30% chutado
    query_parcelas_pagas = SoftDeleteService.get_active_filter(context_id, {
        "status": {"$in": ["pago", "paga"]}
    })
    parcelas_pagas = await db.parcelas.find(
        query_parcelas_pagas, {"_id": 0}
    ).to_list(50000)
    total_juros_recebidos = sum(p.get("valor_juros_centavos", 0) or 0 for p in parcelas_pagas)

    # Juros RECEBIDOS no mês atual: parcelas pagas com data_pagamento dentro do mês
    juros_recebidos_mes = 0
    for p in parcelas_pagas:
        dp = _parse_date(p.get("data_pagamento"))
        if dp and inicio_mes <= dp < fim_mes:
            juros_recebidos_mes += p.get("valor_juros_centavos", 0) or 0

    # ==================== TAXA INADIMPLÊNCIA ====================
    query_total = SoftDeleteService.get_active_filter(context_id)
    total_emprestimos = await db.emprestimos.count_documents(query_total)
    emprestimos_inadimplentes = await db.emprestimos.count_documents(
        SoftDeleteService.get_active_filter(context_id, {"status": "inadimplente"})
    )
    taxa_inadimplencia = (
        emprestimos_inadimplentes / total_emprestimos * 100
    ) if total_emprestimos > 0 else 0

    # ==================== CONTADORES ====================
    total_clientes = await db.clientes.count_documents(
        SoftDeleteService.get_active_filter(context_id, {"status": "ativo"})
    )
    total_emprestimos_ativos = await db.emprestimos.count_documents(
        SoftDeleteService.get_active_filter(context_id, {"status": "ativo"})
    )

    # ==================== PARCELAS EM ATRASO (com valor real + aging) ====================
    parcelas_atrasadas = []
    valor_em_atraso = 0
    aging_buckets = {"1-7": 0, "8-15": 0, "16-30": 0, "30+": 0}
    aging_counts = {"1-7": 0, "8-15": 0, "16-30": 0, "30+": 0}

    a_receber_hoje = 0
    a_receber_semana = 0
    a_receber_mes = 0
    juros_a_receber_mes = 0

    for p in parcelas_pendentes:
        venc = _parse_date(p.get("data_vencimento"))
        if not venc:
            continue
        valor_devido = _valor_devido_parcela(p)
        if valor_devido <= 0:
            continue

        # Juros a receber AINDA neste mês: parcelas em aberto vencendo no mês atual
        if inicio_mes <= venc < fim_mes:
            juros_a_receber_mes += p.get("valor_juros_centavos", 0) or 0

        # Atrasada: vencimento < hoje
        if venc < hoje_inicio:
            parcelas_atrasadas.append(p)
            valor_em_atraso += valor_devido
            dias_atraso = (hoje_inicio - venc).days
            if dias_atraso <= 7:
                aging_buckets["1-7"] += valor_devido
                aging_counts["1-7"] += 1
            elif dias_atraso <= 15:
                aging_buckets["8-15"] += valor_devido
                aging_counts["8-15"] += 1
            elif dias_atraso <= 30:
                aging_buckets["16-30"] += valor_devido
                aging_counts["16-30"] += 1
            else:
                aging_buckets["30+"] += valor_devido
                aging_counts["30+"] += 1
        else:
            # A receber (vencimento futuro)
            if venc < fim_hoje:
                a_receber_hoje += valor_devido
            if venc < fim_semana:
                a_receber_semana += valor_devido
            if venc < fim_mes:
                a_receber_mes += valor_devido

    total_parcelas_atrasadas = len(parcelas_atrasadas)

    # ==================== CLIENTES EM ATRASO + TOP INADIMPLENTES ====================
    # Agrupar por empréstimo -> cliente
    emprestimos_map = {e["id"]: e for e in emprestimos}
    cliente_inadimplencia = defaultdict(lambda: {
        "valor_devido": 0,
        "dias_max_atraso": 0,
        "parcelas_atrasadas": 0,
    })

    # Empréstimos das parcelas atrasadas que não estão no mapa: carrega em lote (evita N+1)
    ids_emp_faltantes = {
        p.get("emprestimo_id") for p in parcelas_atrasadas
        if p.get("emprestimo_id") and p.get("emprestimo_id") not in emprestimos_map
    }
    if ids_emp_faltantes:
        docs_emp = await db.emprestimos.find(
            {"id": {"$in": list(ids_emp_faltantes)}, "usuario_id": context_id}, {"_id": 0}
        ).to_list(len(ids_emp_faltantes))
        for d in docs_emp:
            emprestimos_map[d["id"]] = d

    for p in parcelas_atrasadas:
        emp_id = p.get("emprestimo_id")
        emp = emprestimos_map.get(emp_id)
        if not emp:
            continue

        cliente_id = emp.get("cliente_id")
        if not cliente_id:
            continue

        venc = _parse_date(p.get("data_vencimento"))
        dias = (hoje_inicio - venc).days if venc else 0
        valor_devido = _valor_devido_parcela(p)

        info = cliente_inadimplencia[cliente_id]
        info["valor_devido"] += valor_devido
        info["dias_max_atraso"] = max(info["dias_max_atraso"], dias)
        info["parcelas_atrasadas"] += 1

    total_clientes_em_atraso = len(cliente_inadimplencia)

    # Buscar nomes e telefones dos top 10 inadimplentes
    top_inadimplentes = []
    sorted_inadimplentes = sorted(
        cliente_inadimplencia.items(),
        key=lambda x: x[1]["valor_devido"],
        reverse=True
    )[:10]

    if sorted_inadimplentes:
        cliente_ids = [cid for cid, _ in sorted_inadimplentes]
        clientes_docs = await db.clientes.find(
            {"id": {"$in": cliente_ids}, "usuario_id": context_id},
            {"_id": 0, "id": 1, "nome": 1, "telefone": 1}
        ).to_list(50)
        clientes_map = {c["id"]: c for c in clientes_docs}

        for cid, info in sorted_inadimplentes:
            cli = clientes_map.get(cid, {})
            top_inadimplentes.append({
                "cliente_id": cid,
                "cliente_nome": cli.get("nome", "Cliente"),
                "cliente_telefone": cli.get("telefone"),
                "valor_devido_centavos": info["valor_devido"],
                "dias_max_atraso": info["dias_max_atraso"],
                "parcelas_atrasadas": info["parcelas_atrasadas"],
            })

    # ==================== AGING (em ordem fixa) ====================
    aging_atrasos = [
        {"faixa": "1-7 dias", "valor_centavos": aging_buckets["1-7"], "quantidade": aging_counts["1-7"], "color": "#f59e0b"},
        {"faixa": "8-15 dias", "valor_centavos": aging_buckets["8-15"], "quantidade": aging_counts["8-15"], "color": "#f97316"},
        {"faixa": "16-30 dias", "valor_centavos": aging_buckets["16-30"], "quantidade": aging_counts["16-30"], "color": "#ef4444"},
        {"faixa": "30+ dias", "valor_centavos": aging_buckets["30+"], "quantidade": aging_counts["30+"], "color": "#991b1b"},
    ]

    # ==================== PRÓXIMO RECEBIMENTO ====================
    proximo_recebimento = None
    futuras = [
        p for p in parcelas_pendentes
        if _parse_date(p.get("data_vencimento")) and _parse_date(p.get("data_vencimento")) >= hoje_inicio
    ]
    if futuras:
        futuras.sort(key=lambda x: _parse_date(x.get("data_vencimento")))
        prox = futuras[0]
        emp = emprestimos_map.get(prox.get("emprestimo_id"))
        if not emp:
            emp = await db.emprestimos.find_one(
                {"id": prox.get("emprestimo_id"), "usuario_id": context_id}, {"_id": 0}
            )
        cli_nome = "Cliente"
        if emp and emp.get("cliente_id"):
            cli = await db.clientes.find_one(
                {"id": emp["cliente_id"]}, {"_id": 0, "nome": 1}
            )
            if cli:
                cli_nome = cli.get("nome", "Cliente")
        proximo_recebimento = {
            "parcela_id": prox.get("id"),
            "cliente_nome": cli_nome,
            "data_vencimento": prox.get("data_vencimento"),
            "valor_centavos": _valor_devido_parcela(prox),
            "numero_parcela": prox.get("numero_parcela"),
        }

    # ==================== RECEBIDO MÊS ATUAL (somar pagamentos do mês) ====================
    pagamentos_mes = await db.pagamentos.find(
        SoftDeleteService.get_active_filter(context_id, {}),
        {"_id": 0, "valor_pago_centavos": 1, "data_pagamento": 1}
    ).to_list(50000)

    recebido_mes_atual = 0
    for pg in pagamentos_mes:
        dp = _parse_date(pg.get("data_pagamento"))
        if dp and inicio_mes <= dp < fim_mes:
            recebido_mes_atual += pg.get("valor_pago_centavos", 0) or 0

    # ==================== PRÓXIMOS VENCIMENTOS (7 dias) - lista ====================
    proximos_vencimentos = []
    futuras_7d = sorted(
        [p for p in futuras if _parse_date(p.get("data_vencimento")) < fim_semana],
        key=lambda x: _parse_date(x.get("data_vencimento"))
    )[:10]
    cli_ids_7d = {
        emprestimos_map[p.get("emprestimo_id")].get("cliente_id")
        for p in futuras_7d
        if emprestimos_map.get(p.get("emprestimo_id"))
    }
    cli_ids_7d.discard(None)
    clientes_7d = {}
    if cli_ids_7d:
        docs_cli = await db.clientes.find(
            {"id": {"$in": list(cli_ids_7d)}, "usuario_id": context_id},
            {"_id": 0, "id": 1, "nome": 1}
        ).to_list(len(cli_ids_7d))
        clientes_7d = {c["id"]: c for c in docs_cli}
    for p in futuras_7d:
        emp = emprestimos_map.get(p.get("emprestimo_id"))
        if not emp:
            continue
        cli = clientes_7d.get(emp.get("cliente_id"))
        proximos_vencimentos.append({
            "parcela_id": p.get("id"),
            "emprestimo_id": p.get("emprestimo_id"),
            "cliente_nome": cli.get("nome", "N/A") if cli else "N/A",
            "numero_parcela": p.get("numero_parcela"),
            "data_vencimento": p.get("data_vencimento"),
            "valor_total_centavos": _valor_devido_parcela(p),
        })

    # ========== DADOS PARA GRÁFICOS ==========

    # 1. Evolução Mensal (últimos 12 meses)
    MESES_PT = {1: 'Jan', 2: 'Fev', 3: 'Mar', 4: 'Abr', 5: 'Mai', 6: 'Jun',
                7: 'Jul', 8: 'Ago', 9: 'Set', 10: 'Out', 11: 'Nov', 12: 'Dez'}
    todos_emprestimos = await db.emprestimos.find(
        query_total, {"_id": 0, "created_at": 1, "valor_principal_centavos": 1}
    ).to_list(10000)

    evolucao_mensal = []
    for i in range(11, -1, -1):
        mes_ref = hoje - timedelta(days=30 * i)
        mes_str = f"{MESES_PT[mes_ref.month]}/{mes_ref.strftime('%y')}"
        valor_mes = 0
        for e in todos_emprestimos:
            created = _parse_date(e.get("created_at"))
            if created and created.year == mes_ref.year and created.month == mes_ref.month:
                valor_mes += e.get("valor_principal_centavos", 0)
        evolucao_mensal.append({"mes": mes_str, "valor_centavos": valor_mes})

    # 1b. Evolução de GANHOS mês a mês (juros + multa + mora efetivamente recebidos)
    evolucao_ganhos_mensal = []
    for i in range(11, -1, -1):
        mes_ref = hoje - timedelta(days=30 * i)
        mes_str = f"{MESES_PT[mes_ref.month]}/{mes_ref.strftime('%y')}"
        juros_m = 0
        multa_mora_m = 0
        for p in parcelas_pagas:
            dp = _parse_date(p.get("data_pagamento"))
            if dp and dp.year == mes_ref.year and dp.month == mes_ref.month:
                juros_m += p.get("valor_juros_centavos", 0) or 0
                multa_mora_m += (p.get("valor_multa_centavos", 0) or 0) + (p.get("valor_juros_mora_centavos", 0) or 0)
        evolucao_ganhos_mensal.append({
            "mes": mes_str,
            "juros_centavos": juros_m,
            "multa_mora_centavos": multa_mora_m,
            "total_centavos": juros_m + multa_mora_m,
        })

    # 2. Distribuição por Status
    status_counts = defaultdict(int)
    all_emp = await db.emprestimos.find(
        query_total, {"_id": 0, "status": 1, "metodo_calculo": 1}
    ).to_list(10000)
    for e in all_emp:
        status_counts[e.get("status", "desconhecido")] += 1

    distribuicao_status = [
        {"name": "Ativo", "value": status_counts.get("ativo", 0), "color": "#3b82f6"},
        {"name": "Quitado", "value": status_counts.get("quitado", 0), "color": "#22c55e"},
        {"name": "Inadimplente", "value": status_counts.get("inadimplente", 0), "color": "#ef4444"},
        {"name": "Cancelado", "value": status_counts.get("cancelado", 0), "color": "#6b7280"},
    ]

    # 3. Top 5 Clientes por Valor Emprestado
    cliente_valores = defaultdict(int)
    for e in emprestimos:
        cliente_valores[e.get("cliente_id", "")] += e.get("valor_principal_centavos", 0)

    top_clientes = []
    sorted_clientes = sorted(cliente_valores.items(), key=lambda x: x[1], reverse=True)[:5]
    top_ids = [cid for cid, _ in sorted_clientes if cid]
    top_docs = {}
    if top_ids:
        docs_top = await db.clientes.find(
            {"id": {"$in": top_ids}, "usuario_id": context_id}, {"_id": 0, "id": 1, "nome": 1}
        ).to_list(len(top_ids))
        top_docs = {c["id"]: c for c in docs_top}
    for cliente_id, valor in sorted_clientes:
        cliente = top_docs.get(cliente_id)
        top_clientes.append({
            "nome": (cliente.get("nome", "N/A")[:20] if cliente else "N/A"),
            "valor_centavos": valor
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
        total_capital_emprestado_centavos=total_capital,
        total_juros_a_receber_centavos=total_juros_a_receber,
        total_juros_recebidos_centavos=total_juros_recebidos,
        taxa_inadimplencia=round(taxa_inadimplencia, 2),
        total_clientes_ativos=total_clientes,
        total_emprestimos_ativos=total_emprestimos_ativos,
        total_parcelas_atrasadas=total_parcelas_atrasadas,
        total_clientes_em_atraso=total_clientes_em_atraso,
        valor_em_atraso_centavos=valor_em_atraso,
        a_receber_hoje_centavos=a_receber_hoje,
        a_receber_semana_centavos=a_receber_semana,
        a_receber_mes_centavos=a_receber_mes,
        recebido_mes_atual_centavos=recebido_mes_atual,
        juros_recebidos_mes_centavos=juros_recebidos_mes,
        juros_a_receber_mes_centavos=juros_a_receber_mes,
        proximo_recebimento=proximo_recebimento,
        aging_atrasos=aging_atrasos,
        top_inadimplentes=top_inadimplentes,
        proximos_vencimentos=proximos_vencimentos,
        evolucao_mensal=evolucao_mensal,
        evolucao_ganhos_mensal=evolucao_ganhos_mensal,
        distribuicao_status=distribuicao_status,
        top_clientes=top_clientes,
        metodos_calculo=metodos_calculo,
    )

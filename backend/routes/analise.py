"""
Rotas de Análise e Score de Clientes
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.analise")

from fastapi import APIRouter, HTTPException, Depends, Query
from typing import Optional, List
from datetime import datetime, timezone, timedelta

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.score_service import ScoreService
from services.soft_delete_service import SoftDeleteService

router = APIRouter()


@router.get("/dashboard")
async def obter_dashboard_analise(
    periodo: str = Query("30d", regex="^(30d|90d|1y|all)$"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Dashboard de análise com indicadores gerais
    
    Query Params:
        periodo: "30d", "90d", "1y", "all"
    """
    # Buscar todos os clientes do usuário (dono)
    # Buscar todos os clientes do usuário (dono)
    context_id = get_user_context(current_user)
    
    query_clientes = SoftDeleteService.get_active_filter(context_id)
    clientes = await db.clientes.find(query_clientes).to_list(10000)
    
    total_clientes = len(clientes)
    
    # Contar por classificação
    distribuicao = {
        "A": 0,
        "B": 0,
        "C": 0,
        "D": 0,
        "E": 0
    }
    
    scores = []
    
    for cliente in clientes:
        classificacao = cliente.get("classificacao", "C")
        score = cliente.get("score_atual", 60)
        
        if classificacao in distribuicao:
            distribuicao[classificacao] += 1
        
        scores.append(score)
    
    # Calcular score médio
    score_medio = round(sum(scores) / len(scores), 1) if scores else 60.0
    
    # Classificar por categorias
    bons_pagadores = distribuicao["A"] + distribuicao["B"]
    # Pagadores irregulares = clientes com parcelas atrasadas (não por classificação)
    # Vamos buscar isso do banco
    inadimplentes = distribuicao["D"] + distribuicao["E"]
    
    # Buscar pagadores irregulares (clientes com parcelas vencidas e não pagas)
    query_parcelas = SoftDeleteService.get_active_filter(context_id, {
        "status": "atrasado"
    })
    parcelas_atrasadas = await db.parcelas.find(query_parcelas).to_list(10000)
    
    # IDs únicos de empréstimos com parcelas atrasadas
    emprestimo_ids_atrasados = list(set(p["emprestimo_id"] for p in parcelas_atrasadas))
    
    # Buscar clientes com esses empréstimos
    if emprestimo_ids_atrasados:
        query_emprestimos = SoftDeleteService.get_active_filter(context_id, {
            "id": {"$in": emprestimo_ids_atrasados}
        })
        emprestimos_atrasados = await db.emprestimos.find(query_emprestimos).to_list(10000)
        
        # IDs únicos de clientes irregulares
        clientes_irregulares_ids = list(set(e["cliente_id"] for e in emprestimos_atrasados))
        pagadores_irregulares = len(clientes_irregulares_ids)
    else:
        pagadores_irregulares = 0
    
    # Buscar histórico de scores para evolução
    data_inicio = None
    if periodo == "30d":
        data_inicio = datetime.now(timezone.utc) - timedelta(days=30)
    elif periodo == "90d":
        data_inicio = datetime.now(timezone.utc) - timedelta(days=90)
    elif periodo == "1y":
        data_inicio = datetime.now(timezone.utc) - timedelta(days=365)
    
    query_historico = {"usuario_id": context_id}
    if data_inicio:
        query_historico["created_at"] = {"$gte": data_inicio.isoformat()}
    
    historico = await db.scores_historico.find(query_historico).sort("created_at", 1).to_list(10000)
    
    # Agrupar por mês
    evolucao_mensal = {}
    for registro in historico:
        data = datetime.fromisoformat(registro["created_at"])
        mes_key = data.strftime("%Y-%m")
        
        if mes_key not in evolucao_mensal:
            evolucao_mensal[mes_key] = []
        
        evolucao_mensal[mes_key].append(registro["score"])
    
    # Calcular média por mês
    evolucao = [
        {
            "mes": mes,
            "score_medio": round(sum(scores_mes) / len(scores_mes), 1)
        }
        for mes, scores_mes in sorted(evolucao_mensal.items())
    ]
    
    # Score do mês anterior para comparação
    score_mes_anterior = evolucao[-2]["score_medio"] if len(evolucao) >= 2 else score_medio
    variacao = round(score_medio - score_mes_anterior, 1)
    
    return {
        "resumo": {
            "total_clientes": total_clientes,
            "bons_pagadores": bons_pagadores,
            "pagadores_irregulares": pagadores_irregulares,
            "inadimplentes": inadimplentes
        },
        "distribuicao_classificacao": distribuicao,
        "score_medio": score_medio,
        "tendencias": {
            "score_medio_mes_anterior": score_mes_anterior,
            "variacao": variacao
        },
        "evolucao_mensal": evolucao[-12:]  # Últimos 12 meses
    }


@router.get("/clientes")
async def listar_clientes_com_score(
    classificacao: Optional[str] = Query(None, regex="^[ABCDE]$"),
    score_min: Optional[int] = Query(None, ge=0, le=100),
    score_max: Optional[int] = Query(None, ge=0, le=100),
    ordenar: str = Query("score_desc", regex="^(score_desc|score_asc|nome)$"),
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista clientes com seus scores
    
    Query Params:
        classificacao: Filtrar por A, B, C, D ou E
        score_min: Score mínimo
        score_max: Score máximo
        ordenar: "score_desc", "score_asc", "nome"
        page: Página
        limit: Itens por página
    """
    # Construir query
    context_id = get_user_context(current_user)
    query = SoftDeleteService.get_active_filter(context_id)
    
    if classificacao:
        query["classificacao"] = classificacao
    
    if score_min is not None or score_max is not None:
        query["score_atual"] = {}
        if score_min is not None:
            query["score_atual"]["$gte"] = score_min
        if score_max is not None:
            query["score_atual"]["$lte"] = score_max
    
    # Contar total
    total = await db.clientes.count_documents(query)
    
    # Definir ordenação
    sort_field = "nome"
    sort_direction = 1
    
    if ordenar == "score_desc":
        sort_field = "score_atual"
        sort_direction = -1
    elif ordenar == "score_asc":
        sort_field = "score_atual"
        sort_direction = 1
    
    # Buscar clientes
    skip = (page - 1) * limit
    clientes = await db.clientes.find(query).sort(sort_field, sort_direction).skip(skip).limit(limit).to_list(limit)

    # Batching (sem N+1): buscar de uma vez os empréstimos, parcelas pendentes e último
    # pagamento de TODOS os clientes da página, agrupando em dicionários por cliente.
    cliente_ids = [c["id"] for c in clientes]

    emprestimos_todos = await db.emprestimos.find(
        SoftDeleteService.get_active_filter(context_id, {"cliente_id": {"$in": cliente_ids}})
    ).to_list(None) if cliente_ids else []

    emp_id_to_cliente = {}
    ativos_por_cliente = {}
    for e in emprestimos_todos:
        cid = e.get("cliente_id")
        emp_id_to_cliente[e["id"]] = cid
        if e.get("status") == "ativo":
            ativos_por_cliente[cid] = ativos_por_cliente.get(cid, 0) + 1

    todos_emp_ids = list(emp_id_to_cliente.keys())

    devido_por_cliente = {}
    if todos_emp_ids:
        parcelas_pendentes = await db.parcelas.find(
            SoftDeleteService.get_active_filter(context_id, {
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
                "emprestimo_id": {"$in": todos_emp_ids},
            })
        ).to_list(None)
        for p in parcelas_pendentes:
            cid = emp_id_to_cliente.get(p.get("emprestimo_id"))
            if cid is None:
                continue
            devido_por_cliente[cid] = devido_por_cliente.get(cid, 0) + (
                p.get("valor_total_centavos", 0) - p.get("valor_pago_centavos", 0)
            )

    ultimo_pag_por_cliente = {}
    if todos_emp_ids:
        agrupado = await db.pagamentos.aggregate([
            {"$match": SoftDeleteService.get_active_filter(context_id, {"emprestimo_id": {"$in": todos_emp_ids}})},
            {"$group": {"_id": "$emprestimo_id", "ultimo": {"$max": "$data_pagamento"}}},
        ]).to_list(None)
        for r in agrupado:
            cid = emp_id_to_cliente.get(r["_id"])
            if cid is None or not r.get("ultimo"):
                continue
            atual = ultimo_pag_por_cliente.get(cid)
            if atual is None or r["ultimo"] > atual:
                ultimo_pag_por_cliente[cid] = r["ultimo"]

    # Montar resultado (sem consultas ao banco no laço)
    resultado = []

    for cliente in clientes:
        cid = cliente["id"]
        resultado.append({
            "id": cliente["id"],
            "nome": cliente["nome"],
            "cpf_cnpj": cliente["cpf_cnpj"],
            "score": cliente.get("score_atual", 60),
            "classificacao": cliente.get("classificacao", "C"),
            "emprestimos_ativos": ativos_por_cliente.get(cid, 0),
            "total_devido_centavos": devido_por_cliente.get(cid, 0),
            "ultimo_pagamento": ultimo_pag_por_cliente.get(cid),
            "status": cliente.get("status", "ativo")
        })
    
    return {
        "total": total,
        "page": page,
        "limit": limit,
        "clientes": resultado
    }


@router.get("/score/{cliente_id}")
async def obter_detalhes_score(
    cliente_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Retorna detalhes completos do score de um cliente
    """
    # Verificar se cliente existe e pertence ao usuário
    context_id = get_user_context(current_user)
    cliente = await db.clientes.find_one({
        "id": cliente_id,
        "usuario_id": context_id
    })
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Calcular score atual
    score_data = await ScoreService.calcular_score_cliente(cliente_id, context_id)
    
    if not score_data:
        raise HTTPException(status_code=500, detail="Erro ao calcular score")
    
    # Buscar histórico dos últimos 12 meses
    data_limite = datetime.now(timezone.utc) - timedelta(days=365)
    historico = await db.scores_historico.find({
        "cliente_id": cliente_id,
        "usuario_id": context_id,
        "created_at": {"$gte": data_limite.isoformat()}
    }).sort("created_at", 1).to_list(1000)
    
    # Formatar histórico
    historico_formatado = [
        {
            "data": h["created_at"],
            "score": h["score"]
        }
        for h in historico
    ]
    
    # Determinar recomendação
    score = score_data["score"]
    classificacao = score_data["classificacao"]
    
    if classificacao == "A":
        recomendacao = "elegivel_taxa_reduzida"
    elif classificacao == "B":
        recomendacao = "elegivel_normal"
    elif classificacao == "C":
        recomendacao = "analise_caso_a_caso"
    elif classificacao == "D":
        recomendacao = "condicoes_restritivas"
    else:
        recomendacao = "negar_credito"
    
    return {
        "cliente": {
            "id": cliente["id"],
            "nome": cliente["nome"],
            "cpf_cnpj": cliente["cpf_cnpj"]
        },
        "score": score_data["score"],
        "classificacao": score_data["classificacao"],
        "componentes": score_data["componentes"],
        "metricas": score_data["metricas"],
        "bonus": score_data.get("bonus", 0),
        "recomendacao": recomendacao,
        "historico": historico_formatado,
        "calculado_em": score_data["calculado_em"]
    }


@router.post("/recalcular/{cliente_id}")
async def recalcular_score_cliente(
    cliente_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Recalcula o score de um cliente específico
    """
    # Verificar se cliente existe
    context_id = get_user_context(current_user)
    cliente = await db.clientes.find_one({
        "id": cliente_id,
        "usuario_id": context_id
    })
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Score anterior
    score_anterior = cliente.get("score_atual", 60)
    
    # Recalcular
    score_data = await ScoreService.atualizar_score_cliente(cliente_id, context_id)
    
    if not score_data:
        raise HTTPException(status_code=500, detail="Erro ao recalcular score")
    
    variacao = round(score_data["score"] - score_anterior, 1)
    
    return {
        "message": "Score recalculado com sucesso",
        "score_anterior": score_anterior,
        "score_novo": score_data["score"],
        "classificacao": score_data["classificacao"],
        "variacao": variacao
    }


@router.post("/recalcular-todos")
async def recalcular_todos_scores(
    current_user: Usuario = Depends(get_current_user)
):
    """
    Recalcula os scores de todos os clientes do usuário
    (Executado em foreground - para background, usar Celery)
    """
    # Buscar todos os clientes
    context_id = get_user_context(current_user)
    clientes = await db.clientes.find({
        "usuario_id": context_id
    }).to_list(10000)
    
    total_processados = 0
    erros = 0
    
    for cliente in clientes:
        try:
            await ScoreService.atualizar_score_cliente(cliente["id"], context_id)
            total_processados += 1
        except Exception as e:
            logger.error(f"Erro ao processar cliente {cliente['id']}: {e}")
            erros += 1
    
    return {
        "message": "Recálculo concluído",
        "clientes_processados": total_processados,
        "erros": erros,
        "total_clientes": len(clientes)
    }

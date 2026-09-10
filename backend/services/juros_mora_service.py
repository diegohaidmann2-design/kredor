"""
Serviço de Cálculo de Juros de Mora e Multa por Atraso
"""
from datetime import datetime, timezone
from typing import Dict, Optional
from config import db
from utils.dinheiro import arredondar_centavos
from pymongo import UpdateOne


def _calcular_valores(parcela: dict, emprestimo: Optional[dict], data_referencia: datetime) -> Dict[str, int]:
    """Cálculo puro de multa/juros de mora (sem I/O), reutilizável em lote."""
    # Se já está paga, não calcular
    if parcela.get("status") == "pago":
        return {"valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "dias_atraso": 0, "valor_total_devido_centavos": 0}

    if not emprestimo:
        return {"valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "dias_atraso": 0,
                "valor_total_devido_centavos": parcela.get("valor_total_centavos", 0)}

    data_vencimento = parcela.get("data_vencimento")
    if isinstance(data_vencimento, str):
        data_vencimento = datetime.fromisoformat(data_vencimento.replace('Z', '+00:00'))
    data_venc_date = data_vencimento.date() if isinstance(data_vencimento, datetime) else data_vencimento
    data_ref_date = data_referencia.date() if isinstance(data_referencia, datetime) else data_referencia

    dias_atraso = (data_ref_date - data_venc_date).days if data_ref_date > data_venc_date else 0

    if dias_atraso <= 0:
        return {"valor_multa_centavos": 0, "valor_juros_mora_centavos": 0, "dias_atraso": 0,
                "valor_total_devido_centavos": parcela.get("valor_total_centavos", 0) - parcela.get("valor_pago_centavos", 0)}

    taxa_multa = emprestimo.get("taxa_multa_atraso", 2.0)
    taxa_juros_mora_diario = emprestimo.get("taxa_juros_mora_diario", 0.033)
    valor_base = parcela.get("valor_total_centavos", 0) - parcela.get("valor_pago_centavos", 0)
    valor_multa_centavos = arredondar_centavos(valor_base * (taxa_multa / 100))
    valor_juros_mora_centavos = arredondar_centavos(valor_base * (taxa_juros_mora_diario / 100) * dias_atraso)
    valor_total_devido = valor_base + valor_multa_centavos + valor_juros_mora_centavos

    return {
        "valor_multa_centavos": valor_multa_centavos,
        "valor_juros_mora_centavos": valor_juros_mora_centavos,
        "dias_atraso": dias_atraso,
        "valor_total_devido_centavos": valor_total_devido,
    }


async def calcular_juros_mora_parcela(
    parcela_id: str,
    usuario_id: str,
    data_referencia: Optional[datetime] = None
) -> Dict[str, int]:
    """
    Calcula juros de mora e multa para uma parcela específica
    
    Args:
        parcela_id: ID da parcela
        usuario_id: ID do usuário (contexto)
        data_referencia: Data para cálculo (padrão: hoje)
    
    Returns:
        Dict com: valor_multa_centavos, valor_juros_mora_centavos, dias_atraso, valor_total_devido_centavos
    """
    if data_referencia is None:
        data_referencia = datetime.now(timezone.utc)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": parcela_id,
        "usuario_id": usuario_id,
        "deleted": {"$ne": True}
    })
    
    if not parcela:
        return {
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "dias_atraso": 0,
            "valor_total_devido_centavos": 0
        }
    
    # Se já está paga, não calcular
    if parcela.get("status") == "pago":
        return {
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "dias_atraso": 0,
            "valor_total_devido_centavos": 0
        }
    
    # Buscar empréstimo para pegar taxas
    emprestimo = await db.emprestimos.find_one({
        "id": parcela["emprestimo_id"],
        "usuario_id": usuario_id
    })
    
    return _calcular_valores(parcela, emprestimo, data_referencia)


async def atualizar_juros_mora_parcela(
    parcela_id: str,
    usuario_id: str,
    data_referencia: Optional[datetime] = None
) -> bool:
    """
    Atualiza os valores de juros de mora e multa na parcela
    
    Args:
        parcela_id: ID da parcela
        usuario_id: ID do usuário (contexto)
        data_referencia: Data para cálculo (padrão: hoje)
    
    Returns:
        True se atualizou, False caso contrário
    """
    # Calcular valores
    valores = await calcular_juros_mora_parcela(parcela_id, usuario_id, data_referencia)
    
    if valores["dias_atraso"] <= 0:
        return False
    
    # Atualizar no banco
    result = await db.parcelas.update_one(
        {
            "id": parcela_id,
            "usuario_id": usuario_id,
            "deleted": {"$ne": True}
        },
        {
            "$set": {
                "valor_multa_centavos": valores["valor_multa_centavos"],
                "valor_juros_mora_centavos": valores["valor_juros_mora_centavos"],
                "dias_atraso": valores["dias_atraso"],
                "status": "atrasado",
                "updated_at": datetime.now(timezone.utc).isoformat()
            }
        }
    )
    
    return result.modified_count > 0


async def atualizar_todas_parcelas_atrasadas(usuario_id: Optional[str] = None) -> Dict[str, int]:
    """
    Atualiza juros de mora e multa de todas as parcelas atrasadas
    
    Args:
        usuario_id: ID do usuário específico (None para todos)
    
    Returns:
        Dict com estatísticas: total_processadas, total_atualizadas
    """
    hoje = datetime.now(timezone.utc)
    
    # Filtro base
    filtro = {
        "deleted": {"$ne": True},
        "status": {"$in": ["pendente", "parcial", "atrasado"]}
    }
    
    # Se usuário específico
    if usuario_id:
        filtro["usuario_id"] = usuario_id
    
    # Buscar parcelas pendentes/atrasadas
    parcelas = await db.parcelas.find(filtro).to_list(length=None)

    if not parcelas:
        return {"total_processadas": 0, "total_atualizadas": 0}

    # Carregar todos os empréstimos envolvidos de uma vez (evita N+1 de leitura)
    emprestimo_ids = list({p.get("emprestimo_id") for p in parcelas if p.get("emprestimo_id")})
    emprestimos_map = {}
    if emprestimo_ids:
        async for emp in db.emprestimos.find({"id": {"$in": emprestimo_ids}}):
            emprestimos_map[emp["id"]] = emp

    # Calcular e acumular operações de update num único bulk_write
    operacoes = []
    for parcela in parcelas:
        valores = _calcular_valores(
            parcela,
            emprestimos_map.get(parcela.get("emprestimo_id")),
            hoje,
        )
        if valores["dias_atraso"] <= 0:
            continue
        operacoes.append(UpdateOne(
            {"id": parcela["id"], "usuario_id": parcela["usuario_id"], "deleted": {"$ne": True}},
            {"$set": {
                "valor_multa_centavos": valores["valor_multa_centavos"],
                "valor_juros_mora_centavos": valores["valor_juros_mora_centavos"],
                "dias_atraso": valores["dias_atraso"],
                "status": "atrasado",
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
        ))

    total_atualizadas = 0
    if operacoes:
        resultado = await db.parcelas.bulk_write(operacoes, ordered=False)
        total_atualizadas = (resultado.modified_count or 0)

    return {
        "total_processadas": len(parcelas),
        "total_atualizadas": total_atualizadas
    }


async def obter_resumo_juros_mora(usuario_id: str) -> Dict[str, int]:
    """
    Obtém resumo total de juros de mora e multas do usuário
    
    Args:
        usuario_id: ID do usuário
    
    Returns:
        Dict com: total_multas, total_juros_mora, total_geral
    """
    parcelas = await db.parcelas.find({
        "usuario_id": usuario_id,
        "deleted": {"$ne": True},
        "status": {"$in": ["atrasado", "parcial"]}
    }).to_list(length=None)
    
    total_multas = sum(p.get("valor_multa_centavos", 0) for p in parcelas)
    total_juros_mora = sum(p.get("valor_juros_mora_centavos", 0) for p in parcelas)
    
    return {
        "total_multas_centavos": total_multas,
        "total_juros_mora_centavos": total_juros_mora,
        "total_geral_centavos": total_multas + total_juros_mora
    }

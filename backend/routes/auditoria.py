"""
Rotas de Auditoria
"""
from fastapi import APIRouter, Depends
from typing import Optional
from datetime import datetime, timedelta, timezone

from config import db
from models.usuario import Usuario
from services.auth import require_admin

router = APIRouter()


@router.get("")
async def listar_auditoria(
    acao: Optional[str] = None,
    entidade: Optional[str] = None,
    data_inicio: Optional[str] = None,
    data_fim: Optional[str] = None,
    limite: int = 100,
    current_user: Usuario = Depends(require_admin)
):
    """Lista logs de auditoria (apenas admin)"""
    filtro = {}
    
    if acao:
        filtro["acao"] = {"$regex": acao, "$options": "i"}
    if entidade:
        filtro["entidade"] = {"$regex": entidade, "$options": "i"}
    if data_inicio:
        filtro["created_at"] = {"$gte": data_inicio}
    if data_fim:
        if "created_at" in filtro:
            filtro["created_at"]["$lte"] = data_fim
        else:
            filtro["created_at"] = {"$lte": data_fim}
    
    logs = await db.auditoria.find(filtro, {"_id": 0}).sort("created_at", -1).limit(limite).to_list(limite)
    return logs


@router.get("/estatisticas")
async def estatisticas_auditoria(current_user: Usuario = Depends(require_admin)):
    """Retorna estatísticas de auditoria"""
    hoje = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    inicio_semana = hoje - timedelta(days=7)
    
    total = await db.auditoria.count_documents({})
    hoje_count = await db.auditoria.count_documents({
        "created_at": {"$gte": hoje.isoformat()}
    })
    semana_count = await db.auditoria.count_documents({
        "created_at": {"$gte": inicio_semana.isoformat()}
    })
    
    # Usuários únicos
    pipeline = [
        {"$match": {"created_at": {"$gte": inicio_semana.isoformat()}}},
        {"$group": {"_id": "$usuario_email"}},
        {"$count": "total"}
    ]
    usuarios_ativos = await db.auditoria.aggregate(pipeline).to_list(1)
    usuarios_count = usuarios_ativos[0]["total"] if usuarios_ativos else 0
    
    return {
        "total": total,
        "hoje": hoje_count,
        "ultimos_7_dias": semana_count,
        "usuarios_ativos": usuarios_count
    }

@router.delete("/limpar")
async def limpar_auditoria(current_user: Usuario = Depends(require_admin)):
    """Remove todos os logs de auditoria (apenas admin)"""
    # Em produção, isso deveria ser uma ação restrita a superadmin ou com confirmação extra
    await db.auditoria.delete_many({})
    return {"success": True, "message": "Logs de auditoria limpos com sucesso"}

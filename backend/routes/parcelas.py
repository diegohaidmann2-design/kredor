"""
Rotas de Parcelas
"""
from fastapi import APIRouter, Depends

from config import db
from models.emprestimo import Parcela
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_plano_ativo

router = APIRouter()


@router.get("/pendentes")
async def listar_parcelas_pendentes(current_user: Usuario = Depends(verificar_plano_ativo)):
    """Lista parcelas pendentes do usuário"""
    from services.soft_delete_service import SoftDeleteService
    
    context_id = get_user_context(current_user)
    
    # Usar filtro de soft delete
    query = SoftDeleteService.get_active_filter(context_id)
    query.update({
        "status": {"$in": ["pendente", "parcial", "atrasado"]}
    })
    
    parcelas = await db.parcelas.find(
        query,
        {"_id": 0}
    ).sort("data_vencimento", 1).to_list(1000)
    
    return parcelas

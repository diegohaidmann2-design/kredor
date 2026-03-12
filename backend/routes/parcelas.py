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
    """Lista parcelas pendentes do usuário com informações de cliente e empréstimo"""
    from services.soft_delete_service import SoftDeleteService
    
    context_id = get_user_context(current_user)
    
    # Pipeline de agregação para incluir dados do cliente e empréstimo
    pipeline = [
        # Match - Filtrar parcelas pendentes do usuário
        {
            "$match": {
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "parcial", "atrasado"]}
            }
        },
        # Lookup - Empréstimo PRIMEIRO (para pegar cliente_id)
        {
            "$lookup": {
                "from": "emprestimos",
                "localField": "emprestimo_id",
                "foreignField": "id",
                "as": "emprestimo"
            }
        },
        # Unwind empréstimo
        {"$unwind": {"path": "$emprestimo", "preserveNullAndEmptyArrays": True}},
        # Lookup - Cliente (usando cliente_id do empréstimo)
        {
            "$lookup": {
                "from": "clientes",
                "localField": "emprestimo.cliente_id",
                "foreignField": "id",
                "as": "cliente"
            }
        },
        # Unwind cliente
        {"$unwind": {"path": "$cliente", "preserveNullAndEmptyArrays": True}},
        # Project - Adicionar campos calculados
        {
            "$project": {
                "_id": 0,
                "id": 1,
                "usuario_id": 1,
                "emprestimo_id": 1,
                "numero_parcela": 1,
                "valor_total": 1,
                "valor_pago": 1,
                "valor_multa": 1,
                "valor_juros_mora": 1,
                "data_vencimento": 1,
                "data_pagamento": 1,
                "status": 1,
                "dias_atraso": 1,
                "created_at": 1,
                "updated_at": 1,
                "deleted": 1,
                "cliente_nome": "$cliente.nome",
                "cliente_cpf": "$cliente.cpf_cnpj",
                "cliente_telefone": "$cliente.telefone",
                "valor_emprestimo": "$emprestimo.valor_principal",
                "taxa_juros": "$emprestimo.taxa_juros_mensal",
                "total_parcelas": "$emprestimo.prazo_meses"
            }
        },
        # Ordenar por data de vencimento
        {"$sort": {"data_vencimento": 1}}
    ]
    
    parcelas = await db.parcelas.aggregate(pipeline).to_list(1000)
    
    return parcelas


@router.delete("/{parcela_id}")
async def excluir_parcela(parcela_id: str, current_user: Usuario = Depends(verificar_plano_ativo)):
    """Exclui uma parcela (soft delete)"""
    from services.soft_delete_service import SoftDeleteService
    from services.auditoria_service import AuditoriaService
    from datetime import datetime, timezone
    
    context_id = get_user_context(current_user)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": parcela_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    })
    
    if not parcela:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Verificar se a parcela já foi paga
    if parcela.get("status") == "paga":
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Não é possível excluir uma parcela já paga")
    
    # Soft delete
    soft_delete = SoftDeleteService(db)
    await soft_delete.soft_delete(
        collection="parcelas",
        item_id=parcela_id,
        deleted_by=current_user.email,
        deleted_reason="Excluído pelo usuário"
    )
    
    # Registrar auditoria
    auditoria = AuditoriaService(db)
    await auditoria.registrar(
        collection="parcelas",
        item_id=parcela_id,
        action="delete",
        user_email=current_user.email,
        changes={"status": "deleted"},
        ip_address="127.0.0.1"
    )
    
    return {"message": "Parcela excluída com sucesso"}

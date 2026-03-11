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
        # Lookup - Cliente
        {
            "$lookup": {
                "from": "clientes",
                "localField": "cliente_id",
                "foreignField": "id",
                "as": "cliente"
            }
        },
        # Lookup - Empréstimo
        {
            "$lookup": {
                "from": "emprestimos",
                "localField": "emprestimo_id",
                "foreignField": "id",
                "as": "emprestimo"
            }
        },
        # Unwind - Transformar arrays em objetos
        {"$unwind": {"path": "$cliente", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$emprestimo", "preserveNullAndEmptyArrays": True}},
        # Project - Adicionar campos calculados
        {
            "$project": {
                "_id": 0,
                "id": 1,
                "usuario_id": 1,
                "emprestimo_id": 1,
                "cliente_id": 1,
                "numero_parcela": 1,
                "valor_parcela": 1,
                "valor_total": 1,
                "valor_pago": 1,
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
                "taxa_juros": "$emprestimo.taxa_juros",
                "total_parcelas": "$emprestimo.numero_parcelas"
            }
        },
        # Sort - Ordenar por data de vencimento
        {"$sort": {"data_vencimento": 1}}
    ]
    
    parcelas = await db.parcelas.aggregate(pipeline).to_list(1000)
    
    return parcelas

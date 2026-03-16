"""
Rotas de Pagamentos
"""
from fastapi import APIRouter, HTTPException, Depends, Request
from typing import List
from datetime import datetime, timezone

from config import db
from models.pagamento import Pagamento, PagamentoCreate
from models.notificacao import Notificacao
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_owner
from services.auditoria import registrar_auditoria
from services.permissao_service import verificar_plano_ativo

router = APIRouter()


@router.post("", response_model=Pagamento)
async def registrar_pagamento(
    pagamento: PagamentoCreate,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)  # Verifica plano ativo
):
    """Registra um pagamento"""
    # Apenas o dono da conta pode registrar pagamentos
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    context_id = get_user_context(current_user)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": pagamento.parcela_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if parcela["status"] in ("pago", "paga"):
        raise HTTPException(status_code=400, detail="Parcela já está paga")
    
    # Calcular valor devido
    valor_devido = (
        parcela["valor_total"] - parcela["valor_pago"] +
        parcela.get("valor_multa", 0) + parcela.get("valor_juros_mora", 0)
    )
    
    # Criar pagamento
    data_pagamento = pagamento.data_pagamento or datetime.now(timezone.utc)
    pagamento_obj = Pagamento(
        parcela_id=pagamento.parcela_id,
        emprestimo_id=parcela["emprestimo_id"],
        data_pagamento=data_pagamento,
        valor_pago=pagamento.valor_pago,
        metodo_pagamento=pagamento.metodo_pagamento,
        observacoes=pagamento.observacoes
    )
    
    doc = pagamento_obj.model_dump()
    doc["data_pagamento"] = doc["data_pagamento"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    doc = pagamento_obj.model_dump()
    doc["data_pagamento"] = doc["data_pagamento"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["usuario_id"] = context_id
    doc["created_by"] = current_user.email
    
    await db.pagamentos.insert_one(doc)
    
    # ✅ CORREÇÃO: Usar operador atômico $inc para evitar race condition
    # Atualizar parcela com operação atômica
    result = await db.parcelas.find_one_and_update(
        {
            "id": pagamento.parcela_id,
            "usuario_id": context_id
        },
        {
            "$inc": {"valor_pago": pagamento.valor_pago}  # Operação atômica
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Recalcular status após atualização atômica
    novo_valor_pago = result["valor_pago"]
    valor_devido = (
        result["valor_total"] - novo_valor_pago +
        result.get("valor_multa", 0) + result.get("valor_juros_mora", 0)
    )
    novo_status = "pago" if novo_valor_pago >= valor_devido else "parcial"
    
    update_data = {"status": novo_status}
    
    # Se a parcela foi totalmente paga, registrar a data de pagamento
    if novo_status == "pago":
        update_data["data_pagamento"] = data_pagamento.isoformat()
    
    await db.parcelas.update_one(
        {"id": pagamento.parcela_id},
        {"$set": update_data}
    )
    
    # Verificar se empréstimo foi quitado
    parcelas_pendentes = await db.parcelas.count_documents({
        "emprestimo_id": parcela["emprestimo_id"],
        "usuario_id": context_id,
        "deleted": {"$ne": True},
        "status": {"$in": ["pendente", "atrasado", "parcial"]}
    })
    
    if parcelas_pendentes == 0:
        await db.emprestimos.update_one(
            {"id": parcela["emprestimo_id"], "usuario_id": context_id, "deleted": {"$ne": True}},
            {"$set": {"status": "quitado"}}
        )
    
    # Notificação removida: O próprio usuário que registrou não precisa ser notificado
    # (Solicitacao do usuário: "remova a notificaçao de pagamneto recibido para proprio usurio que lançou")
    
    # Criar notificação de pagamento com dados do cliente (CÓDIGO REMOVIDO)
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="criar",
        entidade="pagamento",
        entidade_id=pagamento_obj.id,
        detalhes=f"Registrou pagamento: R$ {pagamento.valor_pago:,.2f} - {pagamento.metodo_pagamento}",
        dados_novos={"valor": pagamento.valor_pago, "metodo": pagamento.metodo_pagamento},
        ip=request.client.host if request.client else None
    )
    
    return pagamento_obj


@router.get("", response_model=List[Pagamento])
async def listar_pagamentos(current_user: Usuario = Depends(get_current_user)):
    """Lista pagamentos do usuário com informações de cliente, empréstimo e parcela"""
    from services.soft_delete_service import SoftDeleteService

    # Apenas o dono da conta pode ver pagamentos
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    context_id = get_user_context(current_user)
    
    # Pipeline de agregação para incluir dados do cliente, empréstimo e parcela
    pipeline = [
        # Match - Filtrar pagamentos do usuário
        {
            "$match": {
                "usuario_id": context_id,
                "deleted": {"$ne": True}
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
        # Lookup - Parcela
        {
            "$lookup": {
                "from": "parcelas",
                "localField": "parcela_id",
                "foreignField": "id",
                "as": "parcela"
            }
        },
        # Unwind cliente e parcela
        {"$unwind": {"path": "$cliente", "preserveNullAndEmptyArrays": True}},
        {"$unwind": {"path": "$parcela", "preserveNullAndEmptyArrays": True}},
        # Project - Adicionar campos calculados
        {
            "$project": {
                "_id": 0,
                "id": 1,
                "usuario_id": 1,
                "emprestimo_id": 1,
                "parcela_id": 1,
                "valor_pago": 1,
                "data_pagamento": 1,
                "metodo_pagamento": 1,
                "observacoes": 1,
                "created_at": 1,
                "updated_at": 1,
                "deleted": 1,
                "cliente_id": "$emprestimo.cliente_id",
                "cliente_nome": "$cliente.nome",
                "cliente_cpf": "$cliente.cpf_cnpj",
                "cliente_telefone": "$cliente.telefone",
                "valor_emprestimo": "$emprestimo.valor_principal",
                "taxa_juros": "$emprestimo.taxa_juros_mensal",
                "numero_parcela": "$parcela.numero_parcela",
                "total_parcelas": "$emprestimo.prazo_meses"
            }
        },
        # Sort - Ordenar por data de pagamento (mais recentes primeiro)
        {"$sort": {"data_pagamento": -1}}
    ]
    
    pagamentos = await db.pagamentos.aggregate(pipeline).to_list(1000)
    
    # Converter datas se necessário
    for p in pagamentos:
        # Converter data_pagamento se for string, ou usar datetime.now() se for None
        if p.get("data_pagamento"):
            if isinstance(p["data_pagamento"], str):
                p["data_pagamento"] = datetime.fromisoformat(p["data_pagamento"])
        else:
            p["data_pagamento"] = datetime.utcnow()
        
        # Converter created_at se for string, ou usar datetime.now() se for None
        if p.get("created_at"):
            if isinstance(p["created_at"], str):
                p["created_at"] = datetime.fromisoformat(p["created_at"])
        else:
            p["created_at"] = datetime.utcnow()
    
    return pagamentos

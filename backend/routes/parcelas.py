"""
Rotas de Parcelas
"""
from fastapi import APIRouter, Depends, HTTPException
from datetime import datetime, timezone

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
    from services.juros_mora_service import atualizar_juros_mora_parcela
    from datetime import datetime, timezone, timedelta
    
    context_id = get_user_context(current_user)
    
    # Atualizar status, dias de atraso E JUROS DE MORA das parcelas ANTES de listar
    hoje = datetime.now(timezone.utc)
    
    # Buscar todas as parcelas pendentes/parciais/atrasadas para atualizar
    parcelas_para_atualizar = await db.parcelas.find({
        "usuario_id": context_id,
        "deleted": {"$ne": True},
        "status": {"$in": ["pendente", "parcial", "atrasado"]}
    }).to_list(length=None)
    
    for parcela in parcelas_para_atualizar:
        try:
            # ✅ NOVO: Atualizar juros de mora automaticamente
            await atualizar_juros_mora_parcela(
                parcela["id"],
                context_id,
                hoje
            )
        except Exception as e:
            print(f"Erro ao atualizar juros de mora da parcela {parcela.get('id')}: {e}")
            continue
    
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
                "valor_total_centavos": 1,
                "valor_pago_centavos": 1,
                "valor_multa_centavos": 1,
                "valor_juros_mora_centavos": 1,
                "data_vencimento": 1,
                "data_pagamento": 1,
                "status": 1,
                "dias_atraso": 1,
                "created_at": 1,
                "updated_at": 1,
                "deleted": 1,
                "cliente_id": "$cliente.id",
                "cliente_nome": "$cliente.nome",
                "cliente_cpf": "$cliente.cpf_cnpj",
                "cliente_telefone": "$cliente.telefone",
                "valor_emprestimo_centavos": "$emprestimo.valor_principal_centavos",
                "taxa_juros": "$emprestimo.taxa_juros_mensal",
                "total_parcelas": "$emprestimo.prazo_meses",
                "emprestimo_sem_prazo": "$emprestimo.sem_prazo",
                "emprestimo_periodicidade": "$emprestimo.periodicidade",
                "emprestimo_data_inicio": "$emprestimo.data_inicio",
                "emprestimo_taxa_semanal": "$emprestimo.taxa_juros_semanal",
                "emprestimo_taxa_mensal": "$emprestimo.taxa_juros_mensal",
                "ultima_cobranca_em": {"$ifNull": ["$ultima_cobranca_em", None]}
            }
        },
        # Ordenar por data de vencimento
        {"$sort": {"data_vencimento": 1}}
    ]
    
    parcelas = await db.parcelas.aggregate(pipeline).to_list(1000)
    
    # Adicionar total_parcelas calculado dinamicamente por empréstimo
    emprestimos_contagem = {}
    for parcela in parcelas:
        emp_id = parcela.get('emprestimo_id')
        if emp_id and emp_id not in emprestimos_contagem:
            # Contar total de parcelas deste empréstimo
            total = await db.parcelas.count_documents({
                "emprestimo_id": emp_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True}
            })
            emprestimos_contagem[emp_id] = total
        
        parcela['total_parcelas'] = emprestimos_contagem.get(emp_id, 0)
    
    return parcelas


@router.post("/cobrar-em-massa")
async def cobrar_parcelas_em_massa(
    payload: dict,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Envia cobrança via WhatsApp para múltiplas parcelas em uma única chamada.
    payload: { "parcela_ids": [...] }
    Retorna { "enviadas": int, "falhas": int, "detalhes": [...] }
    """
    from services.auth_utils import is_owner
    from routes.whatsapp import enviar_cobranca_parcela as _enviar
    
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")
    
    parcela_ids = payload.get("parcela_ids", [])
    if not isinstance(parcela_ids, list) or not parcela_ids:
        raise HTTPException(status_code=400, detail="Forneça uma lista de parcela_ids")
    
    if len(parcela_ids) > 50:
        raise HTTPException(status_code=400, detail="Máximo de 50 parcelas por lote")
    
    context_id = get_user_context(current_user)
    
    enviadas = 0
    falhas = 0
    detalhes = []
    agora = datetime.now(timezone.utc)
    
    for pid in parcela_ids:
        try:
            resultado = await _enviar(
                parcela_id=pid,
                usar_fila=True,
                current_user=current_user
            )
            enviadas += 1
            await db.parcelas.update_one(
                {"id": pid, "usuario_id": context_id},
                {"$set": {"ultima_cobranca_em": agora.isoformat()}}
            )
            detalhes.append({
                "parcela_id": pid,
                "sucesso": True,
                "mensagem": (resultado or {}).get("message", "Enviado")
            })
        except HTTPException as he:
            falhas += 1
            detalhes.append({
                "parcela_id": pid,
                "sucesso": False,
                "mensagem": str(he.detail)
            })
        except Exception as e:
            falhas += 1
            detalhes.append({"parcela_id": pid, "sucesso": False, "mensagem": str(e)})
    
    return {"enviadas": enviadas, "falhas": falhas, "detalhes": detalhes}


@router.delete("/{parcela_id}")
async def excluir_parcela(parcela_id: str, current_user: Usuario = Depends(verificar_plano_ativo)):
    """Exclui uma parcela (soft delete)"""
    from services.auditoria import registrar_auditoria
    from services.soft_delete_service import SoftDeleteService
    
    context_id = get_user_context(current_user)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": parcela_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    })
    
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Buscar empréstimo para verificar se é sem prazo
    emprestimo = await db.emprestimos.find_one({
        "id": parcela.get("emprestimo_id"),
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    })
    is_sem_prazo = emprestimo.get("sem_prazo", False) if emprestimo else False
    
    # Verificar se a parcela já foi paga
    if parcela.get("status") in ("pago", "paga"):
        raise HTTPException(status_code=400, detail="Não é possível excluir uma parcela já paga")
    
    try:
        ok = await SoftDeleteService.soft_delete(
            collection_name="parcelas",
            document_id=parcela_id,
            usuario_id=context_id,
            motivo="Excluído pelo usuário",
            deleted_by=current_user.email,
        )
        if not ok:
            raise HTTPException(status_code=404, detail="Parcela não encontrada")

        await registrar_auditoria(
            usuario_id=context_id,
            usuario_email=current_user.email,
            acao="delete",
            entidade="parcelas",
            entidade_id=parcela_id,
            detalhes="Parcela excluída (soft delete)",
            dados_anteriores={
                "status": parcela.get("status"),
                "deleted": parcela.get("deleted", False),
            },
            dados_novos={"deleted": True},
        )

        parcelas_pendentes = await db.parcelas.count_documents({
            "emprestimo_id": parcela.get("emprestimo_id"),
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]},
        })
        
        # Recalcular os valores do empréstimo com base nas parcelas ativas
        parcelas_ativas = await db.parcelas.find({
            "emprestimo_id": parcela.get("emprestimo_id"),
            "usuario_id": context_id,
            "deleted": {"$ne": True}
        }).to_list(None)
        
        # Calcular novo valor total e prazo
        novo_valor_total = sum(p.get("valor_total_centavos", 0) for p in parcelas_ativas)
        novo_prazo_meses = len(parcelas_ativas)
        
        # Calcular valor pago
        valor_pago_centavos = sum(p.get("valor_pago_centavos", 0) for p in parcelas_ativas if p.get("status") == "pago")
        
        # Atualizar empréstimo
        update_data = {
            "valor_total_com_juros_centavos": novo_valor_total,
            "prazo_meses": novo_prazo_meses,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }
        
        # Se não há mais parcelas pendentes e NÃO é sem_prazo, marcar como quitado
        if parcelas_pendentes == 0 and novo_prazo_meses > 0 and not is_sem_prazo:
            update_data["status"] = "quitado"
        
        await db.emprestimos.update_one(
            {"id": parcela.get("emprestimo_id"), "usuario_id": context_id, "deleted": {"$ne": True}},
            {"$set": update_data}
        )
    except HTTPException:
        raise
    except Exception:
        raise HTTPException(status_code=500, detail="Erro interno ao excluir parcela")
    
    return {"message": "Parcela excluída com sucesso"}


@router.get("/resumo-juros-mora")
async def obter_resumo_juros_mora(current_user: Usuario = Depends(verificar_plano_ativo)):
    """
    Obtém resumo total de juros de mora e multas do usuário
    
    Retorna:
    - total_multas: Total de multas acumuladas
    - total_juros_mora: Total de juros de mora acumulados
    - total_geral: Soma de multas + juros de mora
    """
    from services.juros_mora_service import obter_resumo_juros_mora
    
    context_id = get_user_context(current_user)
    resumo = await obter_resumo_juros_mora(context_id)
    
    return resumo



@router.delete("/{parcela_id}")
async def deletar_parcela(
    parcela_id: str,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Deleta (soft delete) uma parcela"""
    from services.auth_utils import is_owner
    from services.auditoria import registrar_auditoria
    from datetime import datetime, timezone
    from fastapi import Request
    
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Apenas o dono pode excluir parcelas")
    
    context_id = get_user_context(current_user)
    
    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": parcela_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    })
    
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    # Bloquear exclusão de parcela paga
    if parcela.get("status") == "pago":
        raise HTTPException(status_code=400, detail="Não é possível excluir parcela já paga")
    
    # Soft delete
    await db.parcelas.update_one(
        {"id": parcela_id, "usuario_id": context_id},
        {"$set": {"deleted": True, "updated_at": datetime.now(timezone.utc).isoformat()}}
    )
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="excluir",
        entidade="parcelas",
        entidade_id=parcela_id,
        detalhes=f"Excluiu parcela #{parcela.get('numero_parcela')}",
        dados_anteriores={"numero_parcela": parcela.get("numero_parcela"), "valor_total_centavos": parcela.get("valor_total_centavos")},
        ip=None,
        user_agent=None
    )
    
    return {"message": "Parcela excluída com sucesso"}

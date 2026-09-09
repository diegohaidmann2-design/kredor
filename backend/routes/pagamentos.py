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
from services.parcela_service import inserir_parcela_juros_aberto
from services.inadimplencia_service import recalcular_status_emprestimo
from services.score_service import ScoreService
from services.logging_service import get_logger
from utils.dinheiro import formatar_reais
from utils.transacao import transacao

logger = get_logger("gestorcred.pagamentos")

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

    # Fix #7 (melhorado): Validar valor ANTES de qualquer query no banco
    if pagamento.valor_pago_centavos <= 0:
        raise HTTPException(status_code=422, detail="O valor do pagamento deve ser maior que zero")

    # Buscar parcela
    parcela = await db.parcelas.find_one({
        "id": pagamento.parcela_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not parcela:
        raise HTTPException(status_code=404, detail="Parcela não encontrada")
    
    if parcela["status"] in ("pago", "paga"):
        raise HTTPException(status_code=400, detail="Parcela já está paga")

    valor_maximo = (
        parcela["valor_total_centavos"] - parcela.get("valor_pago_centavos", 0) +
        parcela.get("valor_multa_centavos", 0) + parcela.get("valor_juros_mora_centavos", 0)
    )
    if pagamento.valor_pago_centavos > valor_maximo * 2:
        raise HTTPException(
            status_code=422,
            detail=f"Valor do pagamento (R$ {formatar_reais(pagamento.valor_pago_centavos)}) excede em muito o valor devido (R$ {formatar_reais(valor_maximo)})"
        )
    
    # Calcular valor devido
    valor_devido = (
        parcela["valor_total_centavos"] - parcela["valor_pago_centavos"] +
        parcela.get("valor_multa_centavos", 0) + parcela.get("valor_juros_mora_centavos", 0)
    )
    
    # Buscar empréstimo para pegar informações adicionais
    emprestimo = await db.emprestimos.find_one({
        "id": parcela["emprestimo_id"],
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Criar pagamento com todos os dados necessários para o histórico
    data_pagamento = pagamento.data_pagamento or datetime.now(timezone.utc)
    pagamento_obj = Pagamento(
        parcela_id=pagamento.parcela_id,
        emprestimo_id=parcela["emprestimo_id"],
        data_pagamento=data_pagamento,
        valor_pago_centavos=pagamento.valor_pago_centavos,
        metodo_pagamento=pagamento.metodo_pagamento,
        observacoes=pagamento.observacoes
    )
    
    doc = pagamento_obj.model_dump()
    doc["data_pagamento"] = doc["data_pagamento"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["usuario_id"] = context_id
    doc["created_by"] = current_user.email
    
    # Adicionar dados do cliente e parcela para exibição no histórico
    doc["cliente_id"] = emprestimo.get("cliente_id")
    doc["cliente_nome"] = emprestimo.get("cliente_nome")
    doc["cliente_cpf"] = emprestimo.get("cliente_cpf")
    doc["cliente_telefone"] = emprestimo.get("cliente_telefone")
    doc["valor_emprestimo_centavos"] = emprestimo.get("valor_principal_centavos")
    doc["taxa_juros"] = emprestimo.get("taxa_juros_mensal") or emprestimo.get("taxa_juros_semanal")
    doc["numero_parcela"] = parcela.get("numero_parcela")
    doc["total_parcelas"] = parcela.get("total_parcelas") or emprestimo.get("prazo_meses") or emprestimo.get("prazo_semanas")
    
    # Caminho de dinheiro: pagamento + baixa da parcela + próxima parcela + quitação
    # ficam na mesma transação. Efeitos derivados (auditoria, score, inadimplência)
    # rodam depois do commit.
    async with transacao() as sessao:
        await db.pagamentos.insert_one(doc, session=sessao)

        # Filtro por status na própria query garante que dois pagamentos simultâneos
        # não baixem a mesma parcela duas vezes.
        result = await db.parcelas.find_one_and_update(
            {
                "id": pagamento.parcela_id,
                "usuario_id": context_id,
                "status": {"$nin": ["pago", "paga"]}
            },
            {"$inc": {"valor_pago_centavos": pagamento.valor_pago_centavos}},
            return_document=True,
            session=sessao,
        )

        if not result:
            raise HTTPException(status_code=400, detail="Parcela já está paga ou não encontrada")

        novo_valor_pago = result["valor_pago_centavos"]
        # Valor TOTAL devido da parcela (principal+juros da parcela + multa + juros de mora).
        valor_total_devido = (
            result["valor_total_centavos"] +
            result.get("valor_multa_centavos", 0) + result.get("valor_juros_mora_centavos", 0)
        )
        novo_status = "pago" if novo_valor_pago >= valor_total_devido else "parcial"

        update_data = {"status": novo_status}
        if novo_status == "pago":
            update_data["data_pagamento"] = data_pagamento.isoformat()

        await db.parcelas.update_one(
            {"id": pagamento.parcela_id},
            {"$set": update_data},
            session=sessao,
        )

        # Empréstimo aberto (apenas_juros): manter sempre 1 parcela futura em aberto.
        if novo_status == "pago" and emprestimo.get("sem_prazo") and emprestimo.get("status") in ("ativo", "inadimplente"):
            outras_pendentes = await db.parcelas.count_documents({
                "emprestimo_id": emprestimo["id"],
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            }, session=sessao)

            if outras_pendentes == 0:
                # Inclui deletadas para não reutilizar número
                ultima_parcela = await db.parcelas.find_one(
                    {"emprestimo_id": emprestimo["id"]},
                    {"_id": 0},
                    sort=[("numero_parcela", -1)],
                    session=sessao,
                )
                if ultima_parcela:
                    proximo_numero = ultima_parcela["numero_parcela"] + 1
                    resultado_parcela = await inserir_parcela_juros_aberto(emprestimo, proximo_numero, session=sessao)
                    logger.info(
                        "Parcela gerada automaticamente após pagamento" if resultado_parcela["inserida"]
                        else "Parcela já existia (corrida evitada)",
                        data={"usuario_id": context_id, "emprestimo_id": emprestimo["id"], "numero": proximo_numero},
                    )

        parcelas_pendentes = await db.parcelas.count_documents({
            "emprestimo_id": parcela["emprestimo_id"],
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]}
        }, session=sessao)

        if parcelas_pendentes == 0 and not emprestimo.get("sem_prazo", False):
            await db.emprestimos.update_one(
                {"id": parcela["emprestimo_id"], "usuario_id": context_id, "deleted": {"$ne": True}},
                {"$set": {"status": "quitado"}},
                session=sessao,
            )

    if parcelas_pendentes > 0 or emprestimo.get("sem_prazo", False):
        # Regra unificada: recalcula inadimplência com a MESMA regra do job (30+ dias).
        resultado_status = await recalcular_status_emprestimo(parcela["emprestimo_id"], context_id)
        if resultado_status.get("transicao") == "revertido":
            logger.info("Empréstimo voltou para 'ativo' após pagamento",
                        data={"usuario_id": context_id, "emprestimo_id": parcela["emprestimo_id"]})

    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="criar",
        entidade="pagamento",
        entidade_id=pagamento_obj.id,
        detalhes=f"Registrou pagamento: R$ {formatar_reais(pagamento.valor_pago_centavos)} - {pagamento.metodo_pagamento}",
        dados_novos={"valor_centavos": pagamento.valor_pago_centavos, "metodo": pagamento.metodo_pagamento},
        ip=request.client.host if request.client else None
    )
    
    # Recalcular score do cliente após o pagamento (mantém /analise/clientes atualizado)
    try:
        cliente_id_score = doc.get("cliente_id")
        if cliente_id_score:
            await ScoreService.atualizar_score_cliente(cliente_id_score, context_id)
    except Exception as e:
        logger.warning("Erro ao recalcular score do cliente", data={"usuario_id": context_id, "erro": str(e)})

    return pagamento_obj


@router.get("", response_model=List[Pagamento])
async def listar_pagamentos(current_user: Usuario = Depends(get_current_user)):
    """Lista pagamentos do usuário com informações de cliente, empréstimo e parcela"""
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
                "valor_pago_centavos": 1,
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
                "valor_emprestimo_centavos": "$emprestimo.valor_principal_centavos",
                "taxa_juros": "$emprestimo.taxa_juros_mensal",
                "numero_parcela": "$parcela.numero_parcela",
                "total_parcelas": "$emprestimo.prazo_meses",
                "tipo": {"$ifNull": ["$tipo", "pagamento"]}
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
            p["data_pagamento"] = datetime.now(timezone.utc)
        
        # Converter created_at se for string, ou usar datetime.now() se for None
        if p.get("created_at"):
            if isinstance(p["created_at"], str):
                p["created_at"] = datetime.fromisoformat(p["created_at"])
        else:
            p["created_at"] = datetime.now(timezone.utc)
    
    return pagamentos


@router.delete("/{pagamento_id}")
async def estornar_pagamento(
    pagamento_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Estorna (reverte) um pagamento. Soft-delete + reverte parcela e status do empréstimo."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")
    
    context_id = get_user_context(current_user)
    
    # Buscar pagamento
    pagamento = await db.pagamentos.find_one({
        "id": pagamento_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    }, {"_id": 0})
    
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")
    
    if pagamento.get("tipo") == "amortizacao":
        raise HTTPException(
            status_code=400,
            detail="Amortizações não podem ser estornadas por aqui. Recrie o empréstimo se necessário."
        )

    if pagamento.get("tipo") == "incorporacao_juros":
        raise HTTPException(
            status_code=400,
            detail="Incorporações de juros não podem ser estornadas por aqui."
        )
    
    valor_pago_centavos = pagamento.get("valor_pago_centavos", 0) or 0
    parcela_id = pagamento.get("parcela_id")
    emprestimo_id = pagamento.get("emprestimo_id")
    
    # Estorno: soft-delete do pagamento + reversão da parcela + status do empréstimo, atômicos.
    async with transacao() as sessao:
        await db.pagamentos.update_one(
            {"id": pagamento_id, "usuario_id": context_id},
            {"$set": {
                "deleted": True,
                "deleted_at": datetime.now(timezone.utc).isoformat(),
                "deleted_by": current_user.email,
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }},
            session=sessao,
        )

        parcela_updated = await db.parcelas.find_one_and_update(
            {"id": parcela_id, "usuario_id": context_id},
            {"$inc": {"valor_pago_centavos": -valor_pago_centavos}},
            return_document=True,
            session=sessao,
        )

        if parcela_updated:
            novo_valor_pago = parcela_updated.get("valor_pago_centavos", 0) or 0
            if novo_valor_pago < 0:
                await db.parcelas.update_one(
                    {"id": parcela_id, "usuario_id": context_id},
                    {"$set": {"valor_pago_centavos": 0}},
                    session=sessao,
                )
                novo_valor_pago = 0

            valor_total_centavos = parcela_updated.get("valor_total_centavos", 0) or 0
            venc_str = parcela_updated.get("data_vencimento")
            try:
                venc = datetime.fromisoformat(venc_str.replace("Z", "+00:00")) if isinstance(venc_str, str) else venc_str
            except (ValueError, TypeError, AttributeError):
                venc = None

            hoje = datetime.now(timezone.utc)

            if novo_valor_pago <= 0:
                novo_status = "atrasado" if venc and venc < hoje else "pendente"
            elif novo_valor_pago < valor_total_centavos:
                novo_status = "parcial"
            else:
                novo_status = "pago"

            update_parcela = {"status": novo_status}
            if novo_status != "pago":
                update_parcela["data_pagamento"] = None

            await db.parcelas.update_one(
                {"id": parcela_id, "usuario_id": context_id},
                {"$set": update_parcela},
                session=sessao,
            )

        emp = await db.emprestimos.find_one(
            {"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0}, session=sessao
        )
        if emp and emp.get("status") == "quitado":
            pendentes = await db.parcelas.count_documents({
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]}
            }, session=sessao)
            if pendentes > 0:
                await db.emprestimos.update_one(
                    {"id": emprestimo_id, "usuario_id": context_id},
                    {"$set": {"status": "ativo"}},
                    session=sessao,
                )

    # Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="estornar",
        entidade="pagamento",
        entidade_id=pagamento_id,
        detalhes=f"Estornou pagamento de R$ {formatar_reais(valor_pago_centavos)}",
        dados_anteriores={"valor_pago_centavos": valor_pago_centavos, "parcela_id": parcela_id},
        ip=request.client.host if request.client else None
    )
    
    # Recalcular score do cliente após o estorno
    try:
        cliente_id_score = (emp or {}).get("cliente_id")
        if cliente_id_score:
            await ScoreService.atualizar_score_cliente(cliente_id_score, context_id)
    except Exception as e:
        logger.warning("Erro ao recalcular score do cliente (estorno)", data={"usuario_id": context_id, "erro": str(e)})

    return {"success": True, "message": "Pagamento estornado com sucesso", "valor_estornado_centavos": valor_pago_centavos}

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

    # Fix #7 (melhorado): Validar valor ANTES de qualquer query no banco
    if pagamento.valor_pago <= 0:
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
        parcela["valor_total"] - parcela.get("valor_pago", 0) +
        parcela.get("valor_multa", 0) + parcela.get("valor_juros_mora", 0)
    )
    if pagamento.valor_pago > valor_maximo * 2:
        raise HTTPException(
            status_code=422,
            detail=f"Valor do pagamento (R$ {pagamento.valor_pago:.2f}) excede em muito o valor devido (R$ {valor_maximo:.2f})"
        )
    
    # Calcular valor devido
    valor_devido = (
        parcela["valor_total"] - parcela["valor_pago"] +
        parcela.get("valor_multa", 0) + parcela.get("valor_juros_mora", 0)
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
        valor_pago=pagamento.valor_pago,
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
    doc["valor_emprestimo"] = emprestimo.get("valor_principal")
    doc["taxa_juros"] = emprestimo.get("taxa_juros_mensal") or emprestimo.get("taxa_juros_semanal")
    doc["numero_parcela"] = parcela.get("numero_parcela")
    doc["total_parcelas"] = parcela.get("total_parcelas") or emprestimo.get("prazo_meses") or emprestimo.get("prazo_semanas")
    
    await db.pagamentos.insert_one(doc)
    
    # Fix #8: Operação atômica com filtro de status para evitar race condition
    # Só atualiza se a parcela ainda NÃO estiver paga (previne pagamento duplo)
    result = await db.parcelas.find_one_and_update(
        {
            "id": pagamento.parcela_id,
            "usuario_id": context_id,
            "status": {"$nin": ["pago", "paga"]}  # Garante atomicamente que não está paga
        },
        {
            "$inc": {"valor_pago": pagamento.valor_pago}
        },
        return_document=True
    )
    
    if not result:
        raise HTTPException(status_code=400, detail="Parcela já está paga ou não encontrada")
    
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
    
    # GERAR PRÓXIMA PARCELA PARA EMPRÉSTIMO ABERTO (se parcela foi totalmente paga)
    if novo_status == "pago":
        emprestimo = await db.emprestimos.find_one(
            {"id": parcela["emprestimo_id"]},
            {"_id": 0}
        )
        
        if emprestimo and emprestimo.get("sem_prazo") and emprestimo.get("status") == "ativo":
            # Verificar se já existe alguma parcela pendente/atrasada/parcial.
            # Em emprestimo aberto (apenas_juros), regra: manter sempre 1 parcela
            # futura em aberto. Só gera nova se NÃO houver nenhuma pendente
            # restante após este pagamento.
            outras_pendentes = await db.parcelas.count_documents({
                "emprestimo_id": emprestimo["id"],
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            })
            
            if outras_pendentes == 0:
                # Buscar última parcela (incluindo deletadas, para nao reutilizar numero)
                ultima_parcela = await db.parcelas.find_one(
                    {"emprestimo_id": emprestimo["id"]},
                    {"_id": 0},
                    sort=[("numero_parcela", -1)]
                )
                
                if ultima_parcela:
                    # Gerar próxima parcela
                    from services.calculos import calcular_data_vencimento
                    from models.emprestimo import Parcela as ParcelaModel
                    
                    proximo_numero = ultima_parcela["numero_parcela"] + 1
                    
                    # Calcular juros baseado na periodicidade
                    periodicidade = emprestimo.get("periodicidade", "mensal")
                    if periodicidade == "semanal":
                        taxa_juros = emprestimo.get("taxa_juros_semanal", 0)
                    else:
                        taxa_juros = emprestimo.get("taxa_juros_mensal", 0)
                    
                    juros_periodo = emprestimo["valor_principal"] * (taxa_juros / 100)
                    
                    data_inicio = datetime.fromisoformat(emprestimo["data_inicio"])
                    data_vencimento_nova = calcular_data_vencimento(
                        data_inicio,
                        proximo_numero,
                        emprestimo.get("dia_vencimento"),
                        periodicidade
                    )
                    
                    nova_parcela = ParcelaModel(
                        emprestimo_id=emprestimo["id"],
                        numero_parcela=proximo_numero,
                        data_vencimento=data_vencimento_nova,
                        valor_principal=0.0,
                        valor_juros=round(juros_periodo, 2),
                        valor_total=round(juros_periodo, 2),
                        saldo_devedor=emprestimo["valor_principal"],
                        total_parcelas=None
                    )
                    
                    parcela_doc = nova_parcela.model_dump()
                    parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
                    parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
                    parcela_doc["usuario_id"] = context_id
                    parcela_doc["deleted"] = False  # garantir match do índice único parcial
                    
                    # Insert protegido contra race condition pelo índice único parcial
                    # (emprestimo_id, numero_parcela) onde deleted=false.
                    # Se outra execução (job de 00:10 ou outro pagamento concorrente) já
                    # criou esta parcela, ignoramos silenciosamente.
                    try:
                        await db.parcelas.insert_one(parcela_doc)
                        print(f"✅ Parcela #{proximo_numero} gerada automaticamente após pagamento")
                    except Exception as dup_err:
                        if "duplicate key" in str(dup_err).lower() or "E11000" in str(dup_err):
                            print(f"⏭️  Parcela #{proximo_numero} já existia (race evitada)")
                        else:
                            raise
    
    # Verificar se empréstimo foi quitado
    emprestimo_obj = await db.emprestimos.find_one(
        {"id": parcela["emprestimo_id"], "usuario_id": context_id, "deleted": {"$ne": True}}
    )
    is_sem_prazo = emprestimo_obj.get("sem_prazo", False) if emprestimo_obj else False

    parcelas_pendentes = await db.parcelas.count_documents({
        "emprestimo_id": parcela["emprestimo_id"],
        "usuario_id": context_id,
        "deleted": {"$ne": True},
        "status": {"$in": ["pendente", "atrasado", "parcial"]}
    })
    
    if parcelas_pendentes == 0 and not is_sem_prazo:
        await db.emprestimos.update_one(
            {"id": parcela["emprestimo_id"], "usuario_id": context_id, "deleted": {"$ne": True}},
            {"$set": {"status": "quitado"}}
        )
    else:
        # Fix #10: Se empréstimo estava inadimplente e não há mais parcelas atrasadas → voltar a ativo
        emp_atual = await db.emprestimos.find_one(
            {"id": parcela["emprestimo_id"], "usuario_id": context_id},
            {"_id": 0, "status": 1}
        )
        if emp_atual and emp_atual.get("status") == "inadimplente":
            parcelas_atrasadas = await db.parcelas.count_documents({
                "emprestimo_id": parcela["emprestimo_id"],
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": "atrasado"
            })
            if parcelas_atrasadas == 0:
                await db.emprestimos.update_one(
                    {"id": parcela["emprestimo_id"], "usuario_id": context_id},
                    {"$set": {"status": "ativo"}}
                )
                print(f"✅ Empréstimo {parcela['emprestimo_id']} voltou para 'ativo' após pagamento")
    
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
    
    # Recalcular score do cliente após o pagamento (mantém /analise/clientes atualizado)
    try:
        cliente_id_score = doc.get("cliente_id")
        if cliente_id_score:
            from services.score_service import ScoreService
            await ScoreService.atualizar_score_cliente(cliente_id_score, context_id)
    except Exception as e:
        print(f"⚠️ Erro ao recalcular score do cliente: {e}")

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
            p["data_pagamento"] = datetime.utcnow()
        
        # Converter created_at se for string, ou usar datetime.now() se for None
        if p.get("created_at"):
            if isinstance(p["created_at"], str):
                p["created_at"] = datetime.fromisoformat(p["created_at"])
        else:
            p["created_at"] = datetime.utcnow()
    
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
    
    valor_pago = pagamento.get("valor_pago", 0) or 0
    parcela_id = pagamento.get("parcela_id")
    emprestimo_id = pagamento.get("emprestimo_id")
    
    # Soft-delete do pagamento
    await db.pagamentos.update_one(
        {"id": pagamento_id, "usuario_id": context_id},
        {"$set": {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": current_user.email,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }}
    )
    
    # Reverter valor_pago da parcela atomicamente
    parcela_updated = await db.parcelas.find_one_and_update(
        {"id": parcela_id, "usuario_id": context_id},
        {"$inc": {"valor_pago": -valor_pago}},
        return_document=True
    )
    
    if parcela_updated:
        # Recalcular status da parcela
        novo_valor_pago = parcela_updated.get("valor_pago", 0) or 0
        if novo_valor_pago < 0:
            await db.parcelas.update_one(
                {"id": parcela_id, "usuario_id": context_id},
                {"$set": {"valor_pago": 0}}
            )
            novo_valor_pago = 0
        
        # Recalcular status: pendente, parcial ou atrasado
        valor_total = parcela_updated.get("valor_total", 0) or 0
        venc_str = parcela_updated.get("data_vencimento")
        try:
            venc = datetime.fromisoformat(venc_str.replace("Z", "+00:00")) if isinstance(venc_str, str) else venc_str
        except (ValueError, TypeError, AttributeError):
            venc = None
        
        hoje = datetime.now(timezone.utc)
        
        if novo_valor_pago <= 0:
            novo_status = "atrasado" if venc and venc < hoje else "pendente"
        elif novo_valor_pago < valor_total:
            novo_status = "parcial"
        else:
            novo_status = "pago"
        
        update_parcela = {"status": novo_status}
        # Se parcela voltou para pendente/parcial/atrasado, remover data_pagamento
        if novo_status != "pago":
            update_parcela["data_pagamento"] = None
        
        await db.parcelas.update_one(
            {"id": parcela_id, "usuario_id": context_id},
            {"$set": update_parcela}
        )
    
    # Reverter status do empréstimo se estava quitado
    emp = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0}
    )
    if emp and emp.get("status") == "quitado":
        # Tem parcela pendente novamente -> volta para ativo
        pendentes = await db.parcelas.count_documents({
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]}
        })
        if pendentes > 0:
            await db.emprestimos.update_one(
                {"id": emprestimo_id, "usuario_id": context_id},
                {"$set": {"status": "ativo"}}
            )
    
    # Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="estornar",
        entidade="pagamento",
        entidade_id=pagamento_id,
        detalhes=f"Estornou pagamento de R$ {valor_pago:,.2f}",
        dados_anteriores={"valor_pago": valor_pago, "parcela_id": parcela_id},
        ip=request.client.host if request.client else None
    )
    
    # Recalcular score do cliente após o estorno
    try:
        cliente_id_score = (emp or {}).get("cliente_id")
        if cliente_id_score:
            from services.score_service import ScoreService
            await ScoreService.atualizar_score_cliente(cliente_id_score, context_id)
    except Exception as e:
        print(f"⚠️ Erro ao recalcular score do cliente (estorno): {e}")

    return {"success": True, "message": "Pagamento estornado com sucesso", "valor_estornado": valor_pago}

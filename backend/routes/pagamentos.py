"""
Rotas de Pagamentos
"""
import base64
import io
from xml.sax.saxutils import escape

from fastapi import APIRouter, HTTPException, Depends, Query, Request
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from config import db
from models.pagamento import Pagamento, PagamentoCreate
from models.notificacao import Notificacao
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_owner
from services.auditoria import registrar_auditoria
from services.permissao_service import verificar_plano_ativo
from services.parcela_service import inserir_parcela_juros_aberto, saldo_devedor_emprestimo, saldo_devedor_parcela
from services.inadimplencia_service import recalcular_status_emprestimo
from services.juros_mora_service import calcular_encargos_na_data
from services.score_service import ScoreService
from services.logging_service import get_logger
from services.whatsapp_service import enviar_documento_whatsapp
from utils.dinheiro import formatar_reais
from utils.timezone_utils import now_sp, to_sp, to_utc
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
    
    # A data do pagamento é o dia em que o cliente pagou, informado por quem lança. A tela envia
    # só a data (sem hora), que vale no fuso de Brasília.
    data_pagamento = pagamento.data_pagamento or datetime.now(timezone.utc)
    if data_pagamento.tzinfo is None:
        data_pagamento = to_utc(data_pagamento)
    if data_pagamento > datetime.now(timezone.utc):
        raise HTTPException(status_code=422, detail="A data do pagamento não pode estar no futuro")

    # Multa e mora pela data do pagamento, não pela data do lançamento: receber em dia e lançar
    # dias depois não pode cobrar mora do cliente.
    encargos = calcular_encargos_na_data(parcela, emprestimo, data_pagamento)

    # Criar pagamento com todos os dados necessários para o histórico
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
        # Devido da parcela NA DATA DO PAGAMENTO: parcela + multa e mora daquele dia.
        valor_total_devido = (
            result["valor_total_centavos"]
            + encargos["valor_multa_centavos"] + encargos["valor_juros_mora_centavos"]
        )
        novo_status = "pago" if novo_valor_pago >= valor_total_devido else "parcial"

        # Grava os encargos da data do pagamento: se pagou em dia, zera a mora que o job somou.
        update_data = {"status": novo_status, **encargos}
        if novo_status == "pago":
            update_data["data_pagamento"] = data_pagamento.isoformat()

        await db.parcelas.update_one(
            {"id": pagamento.parcela_id},
            {"$set": update_data},
            session=sessao,
        )

        # Retrato do saldo logo após este pagamento, gravado no próprio pagamento: o recibo
        # tem que mostrar quanto faltava naquela data, não o saldo de quando for emitido.
        parcelas_emprestimo = await db.parcelas.find(
            {"emprestimo_id": parcela["emprestimo_id"], "usuario_id": context_id, "deleted": {"$ne": True}},
            {"_id": 0},
            session=sessao,
        ).to_list(None)
        parcela_apos = {**result, **encargos, "status": novo_status}
        retrato_saldo = {
            "status_parcela_apos": novo_status,
            "saldo_parcela_restante_centavos": saldo_devedor_parcela(parcela_apos),
            "saldo_emprestimo_restante_centavos": saldo_devedor_emprestimo(emprestimo, parcelas_emprestimo),
        }
        await db.pagamentos.update_one(
            {"id": pagamento_obj.id, "usuario_id": context_id},
            {"$set": retrato_saldo},
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

    # Devolve já com o saldo restante, para a tela poder oferecer o recibo na hora.
    return pagamento_obj.model_copy(update=retrato_saldo)


@router.get("", response_model=List[Pagamento])
async def listar_pagamentos(
    emprestimo_id: Optional[str] = Query(None, description="Filtra os pagamentos de um empréstimo"),
    current_user: Usuario = Depends(get_current_user),
):
    """Lista pagamentos do usuário com informações de cliente, empréstimo e parcela"""
    # Apenas o dono da conta pode ver pagamentos
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    context_id = get_user_context(current_user)

    filtro = {"usuario_id": context_id, "deleted": {"$ne": True}}
    if emprestimo_id:
        filtro["emprestimo_id"] = emprestimo_id

    # Pipeline de agregação para incluir dados do cliente, empréstimo e parcela
    pipeline = [
        # Match - Filtrar pagamentos do usuário
        {"$match": filtro},
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
                "tipo": {"$ifNull": ["$tipo", "pagamento"]},
                "status_parcela_apos": 1,
                "saldo_parcela_restante_centavos": 1,
                "saldo_emprestimo_restante_centavos": 1,
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


# ==================== RECIBO DE PAGAMENTO ====================

# Amortização tem recibo próprio (routes/emprestimos.py); incorporação de juros não é dinheiro recebido.
TIPOS_SEM_RECIBO_DE_PAGAMENTO = ["amortizacao", "incorporacao_juros"]


def _formatar_data_sp(valor) -> str:
    """Data do pagamento no fuso de São Paulo (é gravada em UTC)."""
    if isinstance(valor, str):
        try:
            valor = datetime.fromisoformat(valor.replace("Z", "+00:00"))
        except ValueError:
            return "-"
    if not isinstance(valor, datetime):
        return "-"
    return to_sp(valor).strftime("%d/%m/%Y")


async def _carregar_dados_recibo(pagamento_id: str, context_id: str) -> dict:
    """Busca pagamento, empréstimo, parcela e cliente, e resolve os saldos a imprimir."""
    pagamento = await db.pagamentos.find_one(
        {"id": pagamento_id, "usuario_id": context_id, "deleted": {"$ne": True},
         "tipo": {"$nin": TIPOS_SEM_RECIBO_DE_PAGAMENTO}},
        {"_id": 0},
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Pagamento não encontrado")

    emprestimo = await db.emprestimos.find_one(
        {"id": pagamento["emprestimo_id"], "usuario_id": context_id}, {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    parcela = await db.parcelas.find_one(
        {"id": pagamento.get("parcela_id"), "usuario_id": context_id}, {"_id": 0}
    ) or {}
    cliente = await db.clientes.find_one(
        {"id": emprestimo.get("cliente_id"), "usuario_id": context_id}, {"_id": 0}
    ) or {}

    saldo_parcela = pagamento.get("saldo_parcela_restante_centavos")
    saldo_emprestimo = pagamento.get("saldo_emprestimo_restante_centavos")
    # Pagamentos registrados antes do recibo existir não têm o retrato do saldo gravado.
    posicao_atual = saldo_parcela is None or saldo_emprestimo is None
    if posicao_atual:
        parcelas = await db.parcelas.find(
            {"emprestimo_id": emprestimo["id"], "usuario_id": context_id, "deleted": {"$ne": True}},
            {"_id": 0},
        ).to_list(None)
        saldo_parcela = saldo_devedor_parcela(parcela) if parcela else 0
        saldo_emprestimo = saldo_devedor_emprestimo(emprestimo, parcelas)

    return {
        "pagamento": pagamento,
        "emprestimo": emprestimo,
        "parcela": parcela,
        "cliente": cliente,
        "saldo_parcela": int(saldo_parcela),
        "saldo_emprestimo": int(saldo_emprestimo),
        "posicao_atual": posicao_atual,
    }


def _montar_pdf_recibo(dados: dict, credor_nome: Optional[str]) -> io.BytesIO:
    """Monta o PDF do recibo de um pagamento de parcela, total ou parcial."""
    pagamento, emprestimo, parcela, cliente = (
        dados["pagamento"], dados["emprestimo"], dados["parcela"], dados["cliente"]
    )
    saldo_parcela, saldo_emprestimo = dados["saldo_parcela"], dados["saldo_emprestimo"]
    parcial = saldo_parcela > 0

    def moeda(centavos: int) -> str:
        return f"R$ {formatar_reais(centavos)}"

    contrato = f"#{emprestimo['id'][:8].upper()}"
    numero = pagamento.get("numero_parcela") or parcela.get("numero_parcela")
    total_parcelas = pagamento.get("total_parcelas") or parcela.get("total_parcelas")
    if numero and total_parcelas:
        rotulo_parcela = f"{numero} de {total_parcelas}"
    else:
        rotulo_parcela = str(numero) if numero else "-"
    valor_pago = int(pagamento.get("valor_pago_centavos") or 0)
    nome_cliente = cliente.get("nome") or pagamento.get("cliente_nome") or "o cliente"

    estilos = getSampleStyleSheet()
    verde = colors.HexColor("#10b981")
    escuro = colors.HexColor("#1f2937")
    cinza = colors.HexColor("#6b7280")
    claro = colors.HexColor("#f3f4f6")
    titulo = ParagraphStyle("Titulo", parent=estilos["Heading1"], fontSize=20, textColor=verde,
                            alignment=TA_CENTER, spaceAfter=2, fontName="Helvetica-Bold")
    subtitulo = ParagraphStyle("Subtitulo", parent=estilos["Normal"], fontSize=10, textColor=cinza,
                               alignment=TA_CENTER, spaceAfter=12)
    secao = ParagraphStyle("Secao", parent=estilos["Heading2"], fontSize=11, textColor=escuro,
                           spaceBefore=8, spaceAfter=4, fontName="Helvetica-Bold",
                           backColor=claro, borderPadding=(6, 6, 6, 6), leftIndent=6)
    declaracao = ParagraphStyle("Declaracao", parent=estilos["Normal"], fontSize=11, textColor=escuro,
                                alignment=TA_LEFT, leading=18, spaceBefore=8)
    rodape = ParagraphStyle("Rodape", parent=estilos["Normal"], fontSize=7, textColor=cinza,
                            alignment=TA_CENTER)

    def tabela(linhas, linha_destaque=None):
        t = Table(linhas, colWidths=[6 * cm, 11 * cm])
        estilo = [
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
            ("TEXTCOLOR", (0, 0), (0, -1), cinza), ("TEXTCOLOR", (1, 0), (1, -1), escuro),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 6), ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("LINEBELOW", (0, 0), (-1, -2), 0.5, colors.HexColor("#e5e7eb")),
        ]
        if linha_destaque is not None:
            estilo += [
                ("BACKGROUND", (0, linha_destaque), (-1, linha_destaque), claro),
                ("FONTNAME", (0, linha_destaque), (-1, linha_destaque), "Helvetica-Bold"),
                ("FONTSIZE", (0, linha_destaque), (-1, linha_destaque), 12),
                ("TEXTCOLOR", (1, linha_destaque), (1, linha_destaque), verde),
            ]
        t.setStyle(TableStyle(estilo))
        return t

    # Paragraph interpreta marcação: o nome do cliente precisa ser escapado (ex.: "&" quebraria o PDF).
    texto = (
        f"Declaro, para os devidos fins, que recebi de <b>{escape(nome_cliente)}</b> o valor de "
        f"<b>{moeda(valor_pago)}</b>, referente à parcela {rotulo_parcela} do empréstimo de "
        f"contrato <b>{contrato}</b>. "
    )
    if parcial:
        texto += (f"Este pagamento é <b>parcial</b>: permanece em aberto nesta parcela o valor de "
                  f"<b>{moeda(saldo_parcela)}</b>.")
    else:
        texto += "Com este pagamento, a parcela está <b>quitada</b>."

    assinatura = Table([["_" * 40], [credor_nome or "Credor"]], colWidths=[10 * cm])
    assinatura.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("FONTSIZE", (0, 1), (0, 1), 9), ("TEXTCOLOR", (0, 1), (0, 1), cinza),
        ("TOPPADDING", (0, 1), (0, 1), 2),
    ]))

    elementos = [
        Paragraph("RECIBO DE PAGAMENTO PARCIAL" if parcial else "RECIBO DE PAGAMENTO", titulo),
        Paragraph("Kredor - Sistema de Gestão de Empréstimos", subtitulo),
        Paragraph("Dados do Cliente", secao),
        Spacer(1, 0.2 * cm),
        tabela([
            ["Nome:", nome_cliente],
            ["CPF/CNPJ:", cliente.get("cpf_cnpj") or cliente.get("cpf") or "N/A"],
            ["Telefone:", cliente.get("telefone") or "N/A"],
        ]),
        Spacer(1, 0.3 * cm),
        Paragraph("Detalhes do Pagamento", secao),
        Spacer(1, 0.2 * cm),
        tabela([
            ["Contrato:", contrato],
            ["Parcela:", rotulo_parcela],
            ["Data do Pagamento:", _formatar_data_sp(pagamento.get("data_pagamento"))],
            ["Forma de Pagamento:", (pagamento.get("metodo_pagamento") or "N/A").upper()],
            ["VALOR PAGO:", moeda(valor_pago)],
            ["Saldo restante da parcela:", moeda(saldo_parcela)],
            ["Saldo devedor do empréstimo:", moeda(saldo_emprestimo)],
        ], linha_destaque=4),
        Spacer(1, 0.5 * cm),
        Paragraph(texto, declaracao),
        Spacer(1, 1.5 * cm),
        assinatura,
        Spacer(1, 0.8 * cm),
    ]
    if dados["posicao_atual"]:
        elementos += [
            Paragraph(
                "* Este pagamento foi registrado antes de o sistema guardar o saldo no momento do "
                "recebimento; os saldos acima refletem a posição na data de emissão deste recibo.",
                rodape,
            ),
            Spacer(1, 0.2 * cm),
        ]
    elementos.append(Paragraph(
        f"Documento gerado em {now_sp().strftime('%d/%m/%Y às %H:%M')} - Kredor", rodape))

    buffer = io.BytesIO()
    SimpleDocTemplate(buffer, pagesize=A4, topMargin=1.5 * cm, bottomMargin=1.2 * cm,
                      leftMargin=2 * cm, rightMargin=2 * cm).build(elementos)
    buffer.seek(0)
    return buffer


@router.get("/{pagamento_id}/recibo")
async def recibo_pagamento_pdf(pagamento_id: str, current_user: Usuario = Depends(get_current_user)):
    """Recibo (PDF) de um pagamento de parcela, com o valor pago e o saldo que ficou em aberto."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    dados = await _carregar_dados_recibo(pagamento_id, get_user_context(current_user))
    buffer = _montar_pdf_recibo(dados, getattr(current_user, "nome", None))
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="recibo_pagamento_{pagamento_id[:8]}.pdf"'},
    )


@router.post("/{pagamento_id}/recibo/whatsapp")
async def enviar_recibo_pagamento_whatsapp(
    pagamento_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo),
):
    """Envia o recibo (PDF) do pagamento ao cliente pelo WhatsApp conectado do credor."""
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    context_id = get_user_context(current_user)
    dados = await _carregar_dados_recibo(pagamento_id, context_id)

    cliente = dados["cliente"]
    telefone = cliente.get("telefone") or cliente.get("celular")
    if not telefone:
        raise HTTPException(status_code=400, detail="Cliente não possui telefone cadastrado")

    buffer = _montar_pdf_recibo(dados, getattr(current_user, "nome", None))
    valor = formatar_reais(int(dados["pagamento"].get("valor_pago_centavos") or 0))
    legenda = f"Olá {cliente.get('nome', '')}! Segue o recibo do seu pagamento de R$ {valor}."
    if dados["saldo_parcela"] > 0:
        legenda += f" Ficou em aberto nesta parcela: R$ {formatar_reais(dados['saldo_parcela'])}."
    legenda += " Obrigado!"

    resultado = await enviar_documento_whatsapp(
        usuario_id=context_id,
        numero_destino=telefone,
        base64_documento=base64.b64encode(buffer.getvalue()).decode("utf-8"),
        nome_arquivo=f"recibo_pagamento_{pagamento_id[:8]}.pdf",
        legenda=legenda,
    )
    if not resultado.get("success"):
        erro = resultado.get("error")
        # 409 deixa a tela oferecer o envio do recibo em texto pelo WhatsApp Web.
        if erro == "whatsapp_nao_conectado":
            raise HTTPException(status_code=409, detail="WhatsApp não está conectado. Conecte sua conta em Configurações › WhatsApp.")
        if erro == "evolution_nao_configurada":
            raise HTTPException(status_code=400, detail="Integração de WhatsApp não configurada. Configure a Evolution API primeiro.")
        raise HTTPException(status_code=400, detail=resultado.get("message") or "Falha ao enviar pelo WhatsApp")

    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="ENVIAR_RECIBO_WHATSAPP",
        entidade="pagamento",
        entidade_id=pagamento_id,
        detalhes=f"Recibo do pagamento de R$ {valor} enviado por WhatsApp",
        ip=request.client.host if request.client else None,
    )
    return {"success": True, "message": "Recibo enviado pelo WhatsApp."}

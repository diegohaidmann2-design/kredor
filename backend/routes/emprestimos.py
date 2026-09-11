"""
Rotas de Empréstimos
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import io
from pymongo import UpdateOne

from config import db
from models.emprestimo import (
    Emprestimo, EmprestimoCreate, EmprestimoUpdate, Parcela,
    SimulacaoRequest, SimulacaoResponse,
    AmortizacaoRequest, IncorporacaoJurosRequest
)
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context, is_operador_plataforma, is_owner
from utils.dinheiro import arredondar_centavos, formatar_reais
from utils.transacao import transacao
from services.calculos import gerar_parcelas_simulacao
from services.auditoria import registrar_auditoria
from services.permissao_service import verificar_pode_criar_emprestimo, verificar_plano_ativo
from services.pagination_service import paginated_find
from services.soft_delete_service import soft_delete_emprestimo, SoftDeleteService
from services.logging_service import get_logger
from services.soft_delete_service import restore_emprestimo
from utils.relatorio_templates import gerar_pdf_profissional
from utils.excel_templates import gerar_excel_profissional
import uuid as _uuid
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import base64
from services.whatsapp_service import enviar_documento_whatsapp
from services.parcela_service import STATUS_PARCELA_QUITADA, imputar_pagamento_parcela, saldo_devedor_emprestimo
import uuid
from models.emprestimo import ProrrogacaoRequest, ProrrogacaoResponse
from services.calculos import calcular_data_vencimento
import uuid as _uuid_hist

router = APIRouter()


def executar_simulacao(simulacao: SimulacaoRequest) -> SimulacaoResponse:
    """Fonte única do cálculo financeiro: valida e gera as parcelas de uma simulação.

    Não toca banco nem exige contexto de usuário — é aritmética pura em centavos,
    reutilizada tanto pela rota autenticada quanto pela calculadora pública.
    """
    # Validar campos obrigatórios baseado na periodicidade
    if simulacao.periodicidade == "semanal":
        if not simulacao.taxa_juros_semanal or not simulacao.prazo_semanas:
            raise HTTPException(
                status_code=422,
                detail="Para simulação semanal, taxa_juros_semanal e prazo_semanas são obrigatórios"
            )
    elif simulacao.periodicidade == "diario":
        if simulacao.taxa_juros_diaria is None or not simulacao.prazo_dias:
            raise HTTPException(
                status_code=422,
                detail="Para simulação diária, taxa_juros_diaria e prazo_dias são obrigatórios"
            )
    else:  # mensal
        if not simulacao.taxa_juros_mensal or not simulacao.prazo_meses:
            raise HTTPException(
                status_code=422,
                detail="Para simulação mensal, taxa_juros_mensal e prazo_meses são obrigatórios"
            )

    data_inicio = simulacao.data_inicio or datetime.now(timezone.utc)
    parcelas = gerar_parcelas_simulacao(simulacao, data_inicio, simulacao.dia_vencimento)

    valor_total_centavos = sum(p.valor_total_centavos for p in parcelas)
    valor_juros_centavos = valor_total_centavos - simulacao.valor_principal_centavos

    return SimulacaoResponse(
        valor_principal_centavos=simulacao.valor_principal_centavos,
        taxa_juros_mensal=simulacao.taxa_juros_mensal,
        prazo_meses=simulacao.prazo_meses,
        metodo_calculo=simulacao.metodo_calculo,
        periodo_carencia_meses=simulacao.periodo_carencia_meses,
        periodicidade=simulacao.periodicidade,
        taxa_juros_semanal=simulacao.taxa_juros_semanal,
        prazo_semanas=simulacao.prazo_semanas,
        taxa_juros_diaria=simulacao.taxa_juros_diaria,
        prazo_dias=simulacao.prazo_dias,
        valor_total_com_juros_centavos=valor_total_centavos,
        valor_total_juros_centavos=valor_juros_centavos,
        parcelas=parcelas
    )


@router.post("/simular", response_model=SimulacaoResponse)
async def simular_emprestimo(
    simulacao: SimulacaoRequest,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Simula um empréstimo (área logada)."""
    return executar_simulacao(simulacao)


@router.post("/simular-publico", response_model=SimulacaoResponse)
async def simular_emprestimo_publico(simulacao: SimulacaoRequest):
    """Simulação pública da calculadora da landing.

    Mesma fonte de cálculo da rota autenticada, sem exigir login: garante que a
    conta mostrada ao visitante nunca divirja do que o backend gera no contrato.
    """
    return executar_simulacao(simulacao)


@router.post("", response_model=Emprestimo)
async def criar_emprestimo(
    emprestimo: EmprestimoCreate,
    request: Request,
    current_user: Usuario = Depends(verificar_pode_criar_emprestimo)  # Verifica plano + limite
):
    """Cria um novo empréstimo"""
    context_id = get_user_context(current_user)
    
    # Validar empréstimo sem prazo
    if emprestimo.sem_prazo:
        # Empréstimo aberto: apenas juros (mensal ou semanal)
        if emprestimo.metodo_calculo != "apenas_juros":
            raise HTTPException(
                status_code=422,
                detail="Empréstimo sem prazo deve usar método 'apenas_juros'"
            )
        
        # Validar taxa de juros baseado na periodicidade
        if emprestimo.periodicidade == "semanal":
            if not emprestimo.taxa_juros_semanal:
                raise HTTPException(
                    status_code=422,
                    detail="Taxa de juros semanal é obrigatória para empréstimo sem prazo semanal"
                )
            # Forçar prazo None
            emprestimo.prazo_semanas = None
        else:  # mensal
            if not emprestimo.taxa_juros_mensal:
                raise HTTPException(
                    status_code=422,
                    detail="Taxa de juros mensal é obrigatória para empréstimo sem prazo mensal"
                )
            # Forçar prazo None
            emprestimo.prazo_meses = None
    else:
        # Validar campos obrigatórios baseado na periodicidade
        if emprestimo.periodicidade == "semanal":
            if not emprestimo.taxa_juros_semanal or not emprestimo.prazo_semanas:
                raise HTTPException(
                    status_code=422, 
                    detail="Para empréstimo semanal, taxa_juros_semanal e prazo_semanas são obrigatórios"
                )
        else:  # mensal
            if not emprestimo.taxa_juros_mensal or not emprestimo.prazo_meses:
                raise HTTPException(
                    status_code=422, 
                    detail="Para empréstimo mensal, taxa_juros_mensal e prazo_meses são obrigatórios"
                )
    
    # Verificar se cliente pertence ao usuário
    cliente = await db.clientes.find_one({
        "id": emprestimo.cliente_id,
        "usuario_id": context_id
    })
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    if cliente.get("status") == "bloqueado":
        raise HTTPException(status_code=400, detail="Cliente bloqueado")
    
    # Para empréstimos sem prazo, gerar parcelas até cobrir a data atual
    if emprestimo.sem_prazo:
        data_inicio = emprestimo.data_inicio or datetime.now(timezone.utc)
        hoje = datetime.now(timezone.utc)
        
        # Calcular juros baseado na periodicidade
        if emprestimo.periodicidade == "semanal":
            taxa_juros = emprestimo.taxa_juros_semanal
            periodicidade_label = "semanal"
        else:  # mensal
            taxa_juros = emprestimo.taxa_juros_mensal
            periodicidade_label = "mensal"
        
        juros_periodo = arredondar_centavos(emprestimo.valor_principal_centavos * (taxa_juros / 100))
        
        # Criar empréstimo
        emprestimo_data = emprestimo.model_dump()
        emprestimo_data["data_inicio"] = data_inicio
        emprestimo_data["valor_total_com_juros_centavos"] = 0  # Será calculado ao quitar
        emprestimo_data["valor_total_juros_centavos"] = 0  # Será calculado ao quitar
        
        emprestimo_obj = Emprestimo(**emprestimo_data)
        doc = emprestimo_obj.model_dump()
        doc["data_inicio"] = doc["data_inicio"].isoformat()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["usuario_id"] = context_id
        doc["created_by"] = current_user.email
        
        await db.emprestimos.insert_one(doc)
        
        # Gerar TODAS as parcelas desde data_inicio até ter 1 parcela futura
        numero_parcela = 1
        parcelas_docs = []
        
        while numero_parcela <= 200:  # Segurança contra loop infinito
            data_vencimento = calcular_data_vencimento(
                data_inicio, 
                numero_parcela, 
                emprestimo.dia_vencimento, 
                emprestimo.periodicidade
            )
            
            # Definir status baseado na data
            status_parcela = "atrasado" if data_vencimento < hoje else "pendente"
            
            parcela = Parcela(
                emprestimo_id=emprestimo_obj.id,
                numero_parcela=numero_parcela,
                data_vencimento=data_vencimento,
                valor_principal_centavos=0,
                valor_juros_centavos=juros_periodo,
                valor_total_centavos=juros_periodo,
                saldo_devedor_centavos=emprestimo.valor_principal_centavos,
                total_parcelas=None
            )
            
            parcela_doc = parcela.model_dump()
            parcela_doc["status"] = status_parcela
            parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
            parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
            parcela_doc["usuario_id"] = context_id
            
            parcelas_docs.append(parcela_doc)
            
            # Se esta parcela é futura, paramos (sempre ter 1 pendente)
            if data_vencimento >= hoje:
                break
            
            numero_parcela += 1
        
        # Inserir todas as parcelas de uma vez (sem insert_one em laço)
        if parcelas_docs:
            await db.parcelas.insert_many(parcelas_docs)
        parcelas_criadas = len(parcelas_docs)
        
        # Registrar auditoria
        await registrar_auditoria(
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            acao="CRIAR_EMPRESTIMO_ABERTO",
            entidade="emprestimos",
            entidade_id=emprestimo_obj.id,
            detalhes=f"Criou empréstimo aberto {periodicidade_label}: R$ {formatar_reais(emprestimo.valor_principal_centavos)} - {emprestimo.metodo_calculo} ({parcelas_criadas} parcelas geradas)",
            dados_novos={
                "valor_principal_centavos": emprestimo.valor_principal_centavos, 
                f"taxa_juros_{periodicidade_label}": taxa_juros, 
                "sem_prazo": True,
                "periodicidade": emprestimo.periodicidade,
                "parcelas_geradas": parcelas_criadas
            },
            ip=request.client.host if request.client else None,
            user_agent=request.headers.get("user-agent")
        )
        
        return emprestimo_obj
    
    # Fluxo normal para empréstimos com prazo
    # Simular para obter valores
    simulacao = SimulacaoRequest(
        valor_principal_centavos=emprestimo.valor_principal_centavos,
        taxa_juros_mensal=emprestimo.taxa_juros_mensal,
        prazo_meses=emprestimo.prazo_meses,
        metodo_calculo=emprestimo.metodo_calculo,
        periodo_carencia_meses=emprestimo.periodo_carencia_meses,
        taxa_multa_atraso=emprestimo.taxa_multa_atraso,
        taxa_juros_mora_diario=emprestimo.taxa_juros_mora_diario,
        periodicidade=emprestimo.periodicidade,
        taxa_juros_semanal=emprestimo.taxa_juros_semanal,
        prazo_semanas=emprestimo.prazo_semanas,
        dia_vencimento=emprestimo.dia_vencimento
    )
    
    data_inicio = emprestimo.data_inicio or datetime.now(timezone.utc)
    # ✅ Passar dia_vencimento para cálculo
    parcelas_sim = gerar_parcelas_simulacao(simulacao, data_inicio, emprestimo.dia_vencimento)
    
    valor_total_centavos = sum(p.valor_total_centavos for p in parcelas_sim)
    valor_juros_centavos = valor_total_centavos - emprestimo.valor_principal_centavos
    
    # Criar empréstimo
    emprestimo_data = emprestimo.model_dump()
    emprestimo_data["data_inicio"] = data_inicio
    emprestimo_data["valor_total_com_juros_centavos"] = valor_total_centavos
    emprestimo_data["valor_total_juros_centavos"] = valor_juros_centavos
    
    emprestimo_obj = Emprestimo(**emprestimo_data)
    doc = emprestimo_obj.model_dump()
    doc["data_inicio"] = doc["data_inicio"].isoformat()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["usuario_id"] = context_id
    doc["created_by"] = current_user.email
    
    await db.emprestimos.insert_one(doc)
    
    # Criar parcelas (batch insert para melhor performance)
    parcelas_docs = []
    for p in parcelas_sim:
        parcela_obj = Parcela(
            emprestimo_id=emprestimo_obj.id,
            numero_parcela=p.numero_parcela,
            data_vencimento=datetime.fromisoformat(p.data_vencimento),
            valor_principal_centavos=p.valor_principal_centavos,
            valor_juros_centavos=p.valor_juros_centavos,
            valor_total_centavos=p.valor_total_centavos,
            saldo_devedor_centavos=p.saldo_devedor_centavos
        )
        
        parcela_doc = parcela_obj.model_dump()
        parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
        parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
        parcela_doc["usuario_id"] = context_id
        parcelas_docs.append(parcela_doc)
    
    # Insert em lote (mais eficiente que inserir uma a uma)
    if parcelas_docs:
        await db.parcelas.insert_many(parcelas_docs)
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="criar",
        entidade="emprestimo",
        entidade_id=emprestimo_obj.id,
        detalhes=f"Criou empréstimo: R$ {formatar_reais(emprestimo.valor_principal_centavos)} - {emprestimo.metodo_calculo}",
        dados_novos={
            "valor": emprestimo.valor_principal_centavos,
            "metodo": emprestimo.metodo_calculo,
            "prazo": emprestimo.prazo_meses
        },
        ip=request.client.host if request.client else None
    )
    
    return emprestimo_obj


@router.get("")
async def listar_emprestimos(
    cliente_id: Optional[str] = None,
    status: Optional[str] = None,
    excluir_quitados: bool = Query(False, description="Se True, exclui empréstimos quitados da listagem"),
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=100, description="Itens por página"),
    lixeira: bool = Query(False, description="Se True, lista apenas itens da lixeira (requer permissão)"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista empréstimos do usuário com paginação
    
    Filtros opcionais:
    - cliente_id: Filtrar por cliente específico
    - status: Filtrar por status (ativo, quitado, inadimplente, cancelado)
    - excluir_quitados: Se True, exclui empréstimos quitados (padrão: False)
    - lixeira: Se True, mostra itens deletados (Apenas Admin/Dono)
    
    Retorna:
    - items: Lista de empréstimos
    - pagination: Metadados de paginação
    """
    
    context_id = get_user_context(current_user)
    
    # Se pedir lixeira, verifique permissão
    if lixeira:
        if not (is_operador_plataforma(current_user) or is_owner(current_user)):
             raise HTTPException(status_code=403, detail="Apenas administradores podem acessar a lixeira")
             
        # Usar serviço de soft delete para listar
        result = await SoftDeleteService.list_deleted(
            "emprestimos",
            context_id,
            skip=(page - 1) * limit,
            limit=limit
        )
        
        # Enriquecer com nome do cliente (uma consulta com $in) e formatar datas
        cliente_ids = [item.get("cliente_id") for item in result["items"] if item.get("cliente_id")]
        nomes_clientes = {}
        if cliente_ids:
            async for c in db.clientes.find(
                {"id": {"$in": cliente_ids}, "usuario_id": context_id}, {"_id": 0, "id": 1, "nome": 1}
            ):
                nomes_clientes[c["id"]] = c.get("nome")
        for item in result["items"]:
             item["cliente_nome"] = nomes_clientes.get(item.get("cliente_id"), "Cliente Removido")

             if "deleted_at" in item and isinstance(item["deleted_at"], str):
                 item["deleted_at"] = datetime.fromisoformat(item["deleted_at"])
                 
        # Adaptar formato de retorno para bater com paginação padrão se necessário
        # SoftDeleteService.list_deleted já retorna {total, items}
        return {
            "items": result["items"],
            "total": result["total"],
            "page": page,
            "limit": limit,
            "pages": (result["total"] + limit - 1) // limit
        }
    
    # Query base excluindo deletados
    query = SoftDeleteService.get_active_filter(context_id)
    
    if cliente_id:
        query["cliente_id"] = cliente_id
    if status:
        query["status"] = status
    
    # ✅ Novo: Excluir empréstimos quitados se solicitado
    if excluir_quitados:
        query["status"] = {"$ne": "quitado"}
    
    # Usar paginação
    result = await paginated_find(
        db.emprestimos,
        query,
        page=page,
        limit=limit,
        sort_field="created_at",
        sort_direction=-1
    )
    
    # Pré-carregar o total de juros das parcelas dos empréstimos abertos da página (sem N+1)
    abertos_ids = [e["id"] for e in result["items"] if e.get("sem_prazo")]
    juros_por_emprestimo = {}
    if abertos_ids:
        parcelas_abertos = await db.parcelas.find(
            {"emprestimo_id": {"$in": abertos_ids}, "usuario_id": context_id, "deleted": {"$ne": True}},
            {"_id": 0, "emprestimo_id": 1, "valor_juros_centavos": 1},
        ).to_list(None)
        for p in parcelas_abertos:
            juros_por_emprestimo[p["emprestimo_id"]] = (
                juros_por_emprestimo.get(p["emprestimo_id"], 0) + (p.get("valor_juros_centavos", 0) or 0)
            )

    # Converter datas e calcular total de juros acumulado para empréstimos abertos
    for e in result["items"]:
        if "data_inicio" in e and isinstance(e["data_inicio"], str):
            e["data_inicio"] = datetime.fromisoformat(e["data_inicio"])
        if "created_at" in e and isinstance(e["created_at"], str):
            e["created_at"] = datetime.fromisoformat(e["created_at"])
        
        # Para empréstimos abertos, calcular total de juros das parcelas já geradas
        if e.get("sem_prazo"):
            total_juros_gerado = juros_por_emprestimo.get(e["id"], 0)
            e["valor_total_juros_centavos"] = total_juros_gerado
            e["valor_total_com_juros_centavos"] = e["valor_principal_centavos"] + total_juros_gerado

    await _anexar_resumo_pagamentos(result["items"], context_id)
    return result


async def _anexar_resumo_pagamentos(emprestimos: list, context_id: str) -> None:
    """Acrescenta a cada empréstimo da página o total já recebido e o saldo que falta, para o
    card mostrar sem abrir os detalhes. Duas consultas para a página inteira, nenhuma por empréstimo."""
    ids = [e["id"] for e in emprestimos]
    if not ids:
        return

    parcelas = await db.parcelas.find(
        {"emprestimo_id": {"$in": ids}, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0, "emprestimo_id": 1, "status": 1, "valor_total_centavos": 1, "valor_pago_centavos": 1,
         "valor_multa_centavos": 1, "valor_juros_mora_centavos": 1, "valor_juros_centavos": 1,
         "valor_principal_centavos": 1},
    ).to_list(None)
    # Incorporação de juros não é dinheiro recebido (converte juros em capital), então fica de fora.
    recebidos = await db.pagamentos.aggregate([
        {"$match": {"emprestimo_id": {"$in": ids}, "usuario_id": context_id, "deleted": {"$ne": True},
                    "tipo": {"$ne": "incorporacao_juros"}}},
        {"$group": {"_id": "$emprestimo_id", "total": {"$sum": "$valor_pago_centavos"}, "qtd": {"$sum": 1}}},
    ]).to_list(len(ids))

    parcelas_por_emprestimo = {}
    for p in parcelas:
        parcelas_por_emprestimo.setdefault(p["emprestimo_id"], []).append(p)
    recebido_por_emprestimo = {r["_id"]: r for r in recebidos}

    for e in emprestimos:
        do_emprestimo = parcelas_por_emprestimo.get(e["id"], [])
        recebido = recebido_por_emprestimo.get(e["id"], {})
        e["total_recebido_centavos"] = recebido.get("total", 0)
        e["qtd_pagamentos"] = recebido.get("qtd", 0)
        e["saldo_restante_centavos"] = saldo_devedor_emprestimo(e, do_emprestimo)
        e["parcelas_com_pagamento_parcial"] = sum(1 for p in do_emprestimo if p.get("status") == "parcial")
        # Empréstimo aberto: o card mostra o histórico de juros (pagos e em aberto), não "falta".
        e["juros_pagos_centavos"] = sum(imputar_pagamento_parcela(p)["juros"] for p in do_emprestimo)
        e["juros_em_aberto_centavos"] = sum(
            (p.get("valor_juros_centavos") or 0) - imputar_pagamento_parcela(p)["juros"]
            for p in do_emprestimo if p.get("status") not in STATUS_PARCELA_QUITADA
        )


@router.get("/abertos/resumo")
async def resumo_emprestimos_abertos(current_user: Usuario = Depends(get_current_user)):
    """
    Resumo dos empréstimos ABERTOS (sem_prazo) do usuário:
    juros acumulado (gerado/recebido/em aberto) e a próxima parcela em aberto.
    """
    context_id = get_user_context(current_user)
    hoje = datetime.now(timezone.utc)

    def _parse(v):
        if isinstance(v, datetime):
            return v if v.tzinfo else v.replace(tzinfo=timezone.utc)
        try:
            dt = datetime.fromisoformat(str(v).replace("Z", "+00:00"))
            return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError):
            return None

    emprestimos = await db.emprestimos.find({
        "usuario_id": context_id,
        "sem_prazo": True,
        "status": {"$in": ["ativo", "inadimplente"]},
        "deleted": {"$ne": True},
    }, {"_id": 0}).to_list(1000)

    STATUS_ABERTO = ("pendente", "atrasado", "parcial")
    itens = []
    tot = {"principal": 0, "juros_gerado": 0, "juros_recebido": 0, "juros_em_aberto": 0}

    # Pré-carregar parcelas e nomes de clientes de todos os empréstimos (sem N+1)
    emp_ids = [e["id"] for e in emprestimos]
    parcelas_por_emprestimo = {}
    if emp_ids:
        todas_parcelas = await db.parcelas.find({
            "emprestimo_id": {"$in": emp_ids},
            "usuario_id": context_id,
            "deleted": {"$ne": True},
        }, {"_id": 0}).to_list(None)
        for p in todas_parcelas:
            parcelas_por_emprestimo.setdefault(p["emprestimo_id"], []).append(p)
    cli_ids = [e.get("cliente_id") for e in emprestimos if e.get("cliente_id")]
    nomes_clientes = {}
    if cli_ids:
        for c in await db.clientes.find(
            {"id": {"$in": cli_ids}, "usuario_id": context_id}, {"_id": 0, "id": 1, "nome": 1}
        ).to_list(None):
            nomes_clientes[c["id"]] = c.get("nome")

    for e in emprestimos:
        parcelas = parcelas_por_emprestimo.get(e["id"], [])

        juros_gerado = sum((p.get("valor_juros_centavos") or 0) for p in parcelas)
        juros_recebido = sum((p.get("valor_pago_centavos") or 0) for p in parcelas)
        abertas = [p for p in parcelas if p.get("status") in STATUS_ABERTO]
        juros_em_aberto = sum(
            max((p.get("valor_total_centavos") or 0) - (p.get("valor_pago_centavos") or 0), 0) for p in abertas
        )

        atrasadas = 0
        proxima = None
        for p in abertas:
            venc = _parse(p.get("data_vencimento"))
            if venc and venc < hoje:
                atrasadas += 1
            if proxima is None or (venc and _parse(proxima.get("data_vencimento")) and venc < _parse(proxima.get("data_vencimento"))):
                proxima = p

        nome_cliente = nomes_clientes.get(e.get("cliente_id"), "Cliente")

        proxima_info = None
        if proxima:
            venc = _parse(proxima.get("data_vencimento"))
            dias_atraso = (hoje - venc).days if (venc and venc < hoje) else 0
            proxima_info = {
                "parcela_id": proxima.get("id"),
                "numero_parcela": proxima.get("numero_parcela"),
                "data_vencimento": proxima.get("data_vencimento"),
                "valor_centavos": max((proxima.get("valor_total_centavos") or 0) - (proxima.get("valor_pago_centavos") or 0), 0),
                "status": proxima.get("status"),
                "dias_atraso": dias_atraso,
            }

        periodicidade = e.get("periodicidade", "mensal")
        taxa = e.get("taxa_juros_semanal") if periodicidade == "semanal" else e.get("taxa_juros_mensal")

        itens.append({
            "emprestimo_id": e["id"],
            "cliente_id": e.get("cliente_id"),
            "cliente_nome": nome_cliente,
            "status": e.get("status"),
            "periodicidade": periodicidade,
            "taxa_juros": taxa,
            "valor_principal_centavos": e.get("valor_principal_centavos", 0),
            "juros_gerado_centavos": juros_gerado,
            "juros_recebido_centavos": juros_recebido,
            "juros_em_aberto_centavos": juros_em_aberto,
            "parcelas_atrasadas": atrasadas,
            "total_parcelas": len(parcelas),
            "proxima_parcela": proxima_info,
        })

        tot["principal"] += e.get("valor_principal_centavos", 0) or 0
        tot["juros_gerado"] += juros_gerado
        tot["juros_recebido"] += juros_recebido
        tot["juros_em_aberto"] += juros_em_aberto

    # Ordenar: mais atrasados primeiro, depois maior juros em aberto
    itens.sort(key=lambda x: (-x["parcelas_atrasadas"], -x["juros_em_aberto_centavos"]))

    return {
        "total_emprestimos": len(itens),
        "totais": {f"{k}_centavos": v for k, v in tot.items()},
        "itens": itens,
    }



@router.get("/{emprestimo_id}", response_model=Emprestimo)
async def obter_emprestimo(
    emprestimo_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém um empréstimo específico"""
    context_id = get_user_context(current_user)
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    parcelas_pendentes = await db.parcelas.count_documents({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True},
        "status": {"$in": ["pendente", "atrasado", "parcial"]},
    })
    if parcelas_pendentes == 0 and emprestimo.get("status") != "quitado" and not emprestimo.get("sem_prazo"):
        await db.emprestimos.update_one(
            {"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
            {"$set": {"status": "quitado"}},
        )
        emprestimo["status"] = "quitado"
    
    emprestimo["data_inicio"] = datetime.fromisoformat(emprestimo["data_inicio"])
    emprestimo["created_at"] = datetime.fromisoformat(emprestimo["created_at"])
    return Emprestimo(**emprestimo)


@router.get("/{emprestimo_id}/parcelas", response_model=List[Parcela])
async def listar_parcelas(
    emprestimo_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Lista parcelas de um empréstimo"""
    context_id = get_user_context(current_user)
    
    # Verificar se empréstimo pertence ao usuário
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    })
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    parcelas = await db.parcelas.find(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
        },
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(100)
    
    total_parcelas = len(parcelas)
    
    # Atualizar status de atraso
    hoje = datetime.now(timezone.utc)
    taxa_multa = emprestimo.get("taxa_multa_atraso", 2.0)
    taxa_mora_diario = emprestimo.get("taxa_juros_mora_diario", 0.033)
    
    ops_atraso = []
    for p in parcelas:
        p["data_vencimento"] = datetime.fromisoformat(p["data_vencimento"])
        p["created_at"] = datetime.fromisoformat(p["created_at"])
        p["total_parcelas"] = total_parcelas  # Adicionar campo
        
        if p.get("status") == "paga":
            p["status"] = "pago"

        if p["status"] in ["pendente", "parcial"]:
            data_venc = p["data_vencimento"]
            if data_venc.tzinfo is None:
                data_venc = data_venc.replace(tzinfo=timezone.utc)
            
            if hoje > data_venc:
                dias_atraso = (hoje - data_venc).days
                p["dias_atraso"] = dias_atraso
                p["status"] = "atrasado"
                
                valor_devido = p["valor_total_centavos"] - p["valor_pago_centavos"]
                p["valor_multa_centavos"] = arredondar_centavos(valor_devido * (taxa_multa / 100))
                p["valor_juros_mora_centavos"] = arredondar_centavos(valor_devido * (taxa_mora_diario / 100) * dias_atraso)
                
                ops_atraso.append(UpdateOne(
                    {"id": p["id"], "usuario_id": context_id, "deleted": {"$ne": True}},
                    {"$set": {
                        "dias_atraso": dias_atraso,
                        "status": "atrasado",
                        "valor_multa_centavos": p["valor_multa_centavos"],
                        "valor_juros_mora_centavos": p["valor_juros_mora_centavos"]
                    }}
                ))
    
    # Persistir atualizações de atraso em lote (sem update_one em laço)
    if ops_atraso:
        await db.parcelas.bulk_write(ops_atraso)
    
    return [Parcela(**p) for p in parcelas]


@router.put("/{emprestimo_id}", response_model=Emprestimo)
async def atualizar_emprestimo(
    emprestimo_id: str,
    update_data: EmprestimoUpdate,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Atualiza um empréstimo existente.
    Se campos financeiros forem alterados, as parcelas serão recalculadas.
    Só permite alteração financeira se nenhuma parcela estiver paga.
    """
    context_id = get_user_context(current_user)
    
    # Buscar empréstimo original
    emprestimo_original = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    })
    
    if not emprestimo_original:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Fix #6: Bloquear edição de empréstimo quitado via API
    if emprestimo_original.get("status") == "quitado":
        raise HTTPException(
            status_code=400,
            detail="Não é possível editar um empréstimo quitado. O histórico é imutável."
        )
    
    # Verificar se existem parcelas pagas
    parcelas_pagas = await db.parcelas.count_documents({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id,
        "status": "pago",
        "deleted": {"$ne": True}
    })
    
    # Campos que exigem recálculo de parcelas
    campos_financeiros = [
        "valor_principal_centavos", "taxa_juros_mensal", "taxa_juros_semanal",
        "prazo_meses", "prazo_semanas",
        "metodo_calculo", "periodo_carencia_meses", "data_inicio"
    ]

    def _campo_alterado(campo):
        novo = getattr(update_data, campo)
        if novo is None:
            return False
        original = emprestimo_original.get(campo)
        # data_inicio: o usuário só escolhe a DATA, então comparar apenas a data
        # (evita falso-positivo por diferença de fuso/horário e datetime vs string)
        if campo == "data_inicio":
            try:
                nova_data = novo.date() if isinstance(novo, datetime) else datetime.fromisoformat(str(novo)).date()
            except (ValueError, TypeError):
                return True
            if original is None:
                return True
            try:
                orig_data = (original.date() if isinstance(original, datetime)
                             else datetime.fromisoformat(str(original)).date())
            except (ValueError, TypeError):
                return True
            return nova_data != orig_data
        # Campos numéricos: comparar com tolerância (float vs int/None)
        if isinstance(novo, (int, float)):
            try:
                return abs(float(novo) - float(original if original is not None else 0)) > 1e-9
            except (ValueError, TypeError):
                return True
        return novo != original

    alterou_financeiro = any(_campo_alterado(campo) for campo in campos_financeiros)
    
    if alterou_financeiro and parcelas_pagas > 0:
        raise HTTPException(
            status_code=400, 
            detail="Não é possível alterar valores financeiros de um empréstimo que já possui parcelas pagas. Crie um novo empréstimo ou cancele este."
        )
    
    # Mesclar dados
    updated_dict = {k: v for k, v in update_data.model_dump().items() if v is not None}
    
    # Verificar se é sem_prazo (do update ou do original)
    is_sem_prazo = updated_dict.get("sem_prazo", emprestimo_original.get("sem_prazo", False))
    
    # Se alterou financeiro e NÃO é sem_prazo, recalcular parcelas
    if alterou_financeiro and not is_sem_prazo:
        # Preparar dados para simulação
        periodicidade = updated_dict.get("periodicidade", emprestimo_original.get("periodicidade", "mensal"))
        sim_data = {
            "valor_principal_centavos": updated_dict.get("valor_principal_centavos", emprestimo_original["valor_principal_centavos"]),
            "metodo_calculo": updated_dict.get("metodo_calculo", emprestimo_original["metodo_calculo"]),
            "periodo_carencia_meses": updated_dict.get("periodo_carencia_meses", emprestimo_original.get("periodo_carencia_meses", 0)),
            "taxa_multa_atraso": updated_dict.get("taxa_multa_atraso", emprestimo_original.get("taxa_multa_atraso", 2.0)),
            "taxa_juros_mora_diario": updated_dict.get("taxa_juros_mora_diario", emprestimo_original.get("taxa_juros_mora_diario", 0.033)),
            "periodicidade": periodicidade
        }
        if periodicidade == "semanal":
            sim_data["taxa_juros_semanal"] = updated_dict.get("taxa_juros_semanal", emprestimo_original.get("taxa_juros_semanal"))
            sim_data["prazo_semanas"] = updated_dict.get("prazo_semanas", emprestimo_original.get("prazo_semanas"))
        else:
            sim_data["taxa_juros_mensal"] = updated_dict.get("taxa_juros_mensal", emprestimo_original.get("taxa_juros_mensal"))
            sim_data["prazo_meses"] = updated_dict.get("prazo_meses", emprestimo_original.get("prazo_meses"))
        
        sim_req = SimulacaoRequest(**sim_data)
        data_ini = updated_dict.get("data_inicio")
        if data_ini:
            # Garantir que seja datetime
            if isinstance(data_ini, str):
                data_ini = datetime.fromisoformat(data_ini)
        else:
            data_ini = datetime.fromisoformat(emprestimo_original["data_inicio"])
            
        parcelas_sim = gerar_parcelas_simulacao(sim_req, data_ini)
        
        valor_total_centavos = sum(p.valor_total_centavos for p in parcelas_sim)
        valor_juros_centavos = valor_total_centavos - sim_req.valor_principal_centavos
        
        updated_dict["valor_total_com_juros_centavos"] = valor_total_centavos
        updated_dict["valor_total_juros_centavos"] = valor_juros_centavos
        if "data_inicio" in updated_dict and isinstance(updated_dict["data_inicio"], datetime):
            updated_dict["data_inicio"] = updated_dict["data_inicio"].isoformat()
            
        # Deletar parcelas antigas
        await db.parcelas.delete_many({
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id
        })
        
        # Criar novas parcelas
        parcelas_docs = []
        for p in parcelas_sim:
            parcela_obj = Parcela(
                emprestimo_id=emprestimo_id,
                numero_parcela=p.numero_parcela,
                data_vencimento=datetime.fromisoformat(p.data_vencimento),
                valor_principal_centavos=p.valor_principal_centavos,
                valor_juros_centavos=p.valor_juros_centavos,
                valor_total_centavos=p.valor_total_centavos,
                saldo_devedor_centavos=p.saldo_devedor_centavos
            )
            parcela_doc = parcela_obj.model_dump()
            parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
            parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
            parcela_doc["usuario_id"] = context_id
            parcelas_docs.append(parcela_doc)
            
        if parcelas_docs:
            await db.parcelas.insert_many(parcelas_docs)
    
    # Atualizar empréstimo no banco
    if "data_inicio" in updated_dict and isinstance(updated_dict["data_inicio"], datetime):
        updated_dict["data_inicio"] = updated_dict["data_inicio"].isoformat()
        
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": updated_dict}
    )
    
    # Buscar documento atualizado
    doc_atualizado = await db.emprestimos.find_one({"id": emprestimo_id}, {"_id": 0})
    doc_atualizado["data_inicio"] = datetime.fromisoformat(doc_atualizado["data_inicio"])
    doc_atualizado["created_at"] = datetime.fromisoformat(doc_atualizado["created_at"])
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="editar",
        entidade="emprestimo",
        entidade_id=emprestimo_id,
        detalhes="Atualizou dados do empréstimo",
        dados_novos=updated_dict,
        ip=request.client.host if request.client else None
    )
    
    return Emprestimo(**doc_atualizado)


@router.delete("/{emprestimo_id}")
async def deletar_emprestimo(
    emprestimo_id: str,
    request: Request,
    hard: bool = Query(False, description="Se True, deleta permanentemente"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Deleta um empréstimo e suas parcelas (soft delete por padrão)
    
    - soft delete: Marca como deletado, pode ser restaurado
    - hard delete: Remove permanentemente (usar com cautela)
    """
    
    logger = get_logger("gestorcred.emprestimos")
    context_id = get_user_context(current_user)
    
    # Verificar se empréstimo pertence ao usuário
    # Se for hard delete, permitimos encontrar mesmo se já estiver marcado como deletado
    query = {"id": emprestimo_id, "usuario_id": context_id}
    if not hard:
        query["$or"] = [{"deleted": {"$exists": False}}, {"deleted": False}]
    
    emprestimo = await db.emprestimos.find_one(query)
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    if hard:
        # Hard delete (remoção permanente) é privilégio do operador da plataforma.
        if not is_operador_plataforma(current_user):
            raise HTTPException(
                status_code=403,
                detail="Apenas administradores podem realizar exclusão permanente"
            )
        # Hard delete (remoção permanente)
        # Deletar parcelas associadas
        await db.parcelas.delete_many({
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id
        })
        
        # Deletar pagamentos associados
        await db.pagamentos.delete_many({
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id
        })
        
        # Deletar empréstimo
        result = await db.emprestimos.delete_one({
            "id": emprestimo_id,
            "usuario_id": context_id
        })
        
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
        
        action_msg = "deletado permanentemente"
    else:
        # Soft delete (padrão)
        success = await soft_delete_emprestimo(
            emprestimo_id,
            context_id,
            deleted_by=current_user.email,
            motivo="Deletado pelo usuário"
        )
        if not success:
            raise HTTPException(status_code=500, detail="Erro ao deletar empréstimo")
        
        action_msg = "movido para lixeira"
    
    # Auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="deletar" if hard else "soft_delete",
        entidade="emprestimo",
        entidade_id=emprestimo_id,
        detalhes=f"Empréstimo {action_msg}",
        dados_anteriores={
            "cliente_id": emprestimo.get("cliente_id"),
            "valor_principal_centavos": emprestimo.get("valor_principal_centavos")
        },
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Empréstimo {action_msg}", data={"emprestimo_id": emprestimo_id, "hard": hard})
    
    return {"message": f"Empréstimo {action_msg} com sucesso"}


@router.post("/{emprestimo_id}/restaurar")
async def restaurar_emprestimo(
    emprestimo_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Restaura um empréstimo da lixeira (inclui parcelas e pagamentos)"""
    
    # Verificar permissão
    if not (is_operador_plataforma(current_user) or is_owner(current_user)):
         raise HTTPException(status_code=403, detail="Apenas administradores podem restaurar itens")
    
    logger = get_logger("gestorcred.emprestimos")
    
    context_id = get_user_context(current_user)
    success = await restore_emprestimo(emprestimo_id, context_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado na lixeira")
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="restaurar",
        entidade="emprestimo",
        entidade_id=emprestimo_id,
        detalhes=f"Empréstimo restaurado da lixeira",
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Empréstimo restaurado", data={"emprestimo_id": emprestimo_id})
    
    return {"message": "Empréstimo restaurado com sucesso"}


@router.get("/{emprestimo_id}/exportar")
async def exportar_emprestimo(
    emprestimo_id: str,
    formato: str = "pdf",
    current_user: Usuario = Depends(get_current_user)
):
    """Exporta extrato completo do empréstimo em PDF ou Excel"""
    
    context_id = get_user_context(current_user)
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Buscar cliente
    cliente = await db.clientes.find_one({
        "id": emprestimo["cliente_id"],
        "usuario_id": context_id
    }, {"_id": 0})
    
    # Buscar parcelas
    parcelas = await db.parcelas.find(
        {"emprestimo_id": emprestimo_id, "usuario_id": context_id},
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(100)
    
    # Buscar pagamentos
    pagamentos = await db.pagamentos.find(
        {"emprestimo_id": emprestimo_id, "usuario_id": context_id},
        {"_id": 0}
    ).sort("data_pagamento", 1).to_list(100)
    
    # Calcular totais
    total_pago = sum(p.get("valor_pago_centavos", 0) for p in parcelas if p.get("status") == "pago")
    total_restante = emprestimo["valor_total_com_juros_centavos"] - total_pago
    parcelas_pagas = len([p for p in parcelas if p.get("status") == "pago"])
    parcelas_pendentes = len([p for p in parcelas if p.get("status") in ["pendente", "parcial", "atrasado"]])
    
    # Mapeamento de métodos
    metodo_map = {
        "juros_simples": "Juros Simples",
        "juros_compostos": "Juros Compostos",
        "tabela_price": "Tabela Price",
        "price": "Tabela Price",
        "sac": "SAC",
        "apenas_juros": "Apenas Juros"
    }
    
    status_map = {
        "ativo": "Ativo",
        "quitado": "Quitado",
        "inadimplente": "Inadimplente",
        "cancelado": "Cancelado",
        "pendente": "Pendente",
        "pago": "Pago",
        "atrasado": "Atrasado",
        "parcial": "Parcial"
    }
    
    def formatar_data(data_str):
        if not data_str:
            return "-"
        if isinstance(data_str, str):
            try:
                data = datetime.fromisoformat(data_str.replace("Z", "+00:00"))
                return data.strftime("%d/%m/%Y")
            except Exception:
                return data_str[:10] if len(data_str) > 10 else data_str
        else:
            return data_str.strftime("%d/%m/%Y")
    
    def formatar_moeda(centavos):
        return f"R$ {formatar_reais(centavos)}"
    
    # Preparar dados do resumo executivo
    dados_resumo = [
        {"titulo": "Valor Principal", "valor": formatar_moeda(emprestimo["valor_principal_centavos"]), "cor": "primaria"},
        {"titulo": "Total com Juros", "valor": formatar_moeda(emprestimo["valor_total_com_juros_centavos"]), "cor": "secundaria"},
        {"titulo": "Total Pago", "valor": formatar_moeda(total_pago), "cor": "sucesso"},
        {"titulo": "Saldo Restante", "valor": formatar_moeda(total_restante), "cor": "alerta" if total_restante > 0 else "sucesso"},
        {"titulo": "Parcelas Pagas", "valor": f"{parcelas_pagas}/{len(parcelas)}", "cor": "primaria"},
        {"titulo": "Parcelas Pendentes", "valor": str(parcelas_pendentes), "cor": "erro" if parcelas_pendentes > 0 else "sucesso"},
    ]
    
    # Preparar dados detalhados das parcelas
    dados_parcelas = []
    for p in parcelas:
        dados_parcelas.append({
            "Nº": p["numero_parcela"],
            "Vencimento": formatar_data(p.get("data_vencimento")),
            "Valor": formatar_moeda(p.get("valor_total_centavos", 0)),
            "Valor Pago": formatar_moeda(p.get("valor_pago_centavos", 0)),
            "Status": status_map.get(p.get("status", ""), p.get("status", "")).upper(),
            "Pagamento": formatar_data(p.get("data_pagamento")) if p.get("data_pagamento") else "-"
        })
    
    # Título e período
    titulo = f"Extrato do Empréstimo - {cliente.get('nome', 'Cliente') if cliente else 'Cliente'}"
    data_inicio_fmt = formatar_data(emprestimo.get("data_inicio", emprestimo.get("created_at")))
    periodo = f"{data_inicio_fmt} até {datetime.now().strftime('%d/%m/%Y')}"
    
    # Gerar arquivo com templates profissionais
    if formato == "pdf":
        buffer = gerar_pdf_profissional(
            titulo=titulo,
            periodo=periodo,
            dados=dados_parcelas,
            tipo_relatorio="Extrato de Empréstimo",
            dados_resumo=dados_resumo
        )
        
        return StreamingResponse(
            buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=extrato_emprestimo_{emprestimo_id}_{datetime.now().strftime('%Y%m%d')}.pdf"}
        )
    
    else:  # Excel
        buffer = gerar_excel_profissional(
            titulo=titulo,
            periodo=periodo,
            dados=dados_parcelas,
            tipo_relatorio="Extrato de Empréstimo",
            dados_resumo=dados_resumo
        )
        
        return StreamingResponse(
            buffer,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f"attachment; filename=extrato_emprestimo_{emprestimo_id}_{datetime.now().strftime('%Y%m%d')}.xlsx"}
        )
    



@router.post("/{emprestimo_id}/quitar")
async def quitar_emprestimo_aberto(
    emprestimo_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Quita um empréstimo sem prazo gerando a parcela final (capital + juros)
    """
    context_id = get_user_context(current_user)
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    if not emprestimo.get("sem_prazo"):
        raise HTTPException(status_code=400, detail="Este endpoint é apenas para empréstimos sem prazo")
    
    if emprestimo.get("status") != "ativo":
        raise HTTPException(status_code=400, detail="Empréstimo não está ativo")
    
    # Buscar parcelas EM ABERTO (não pagas) ordenadas por número
    parcelas_abertas = await db.parcelas.find(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]},
        },
        {"_id": 0}
    ).sort("numero_parcela", 1).to_list(1000)

    capital = int(emprestimo.get("valor_principal_centavos", 0) or 0)
    data_pag = datetime.now(timezone.utc)

    if not parcelas_abertas:
        # Se não há nenhuma parcela em aberto (por exemplo, porque foi excluída para dar desconto),
        # criamos uma nova parcela final de quitação com juros R$ 0,00 e o principal = capital.
        last_active = await db.parcelas.find_one(
            {"emprestimo_id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
            sort=[("numero_parcela", -1)]
        )
        numero_final = (last_active.get("numero_parcela", 0) + 1) if last_active else 1
        
        parcela_quitacao_id = str(_uuid.uuid4())
        parcela_quitacao = {
            "id": parcela_quitacao_id,
            "emprestimo_id": emprestimo_id,
            "numero_parcela": numero_final,
            "data_vencimento": data_pag.isoformat(),
            "valor_principal_centavos": capital,
            "valor_juros_centavos": 0,
            "valor_total_centavos": capital,
            "valor_pago_centavos": capital,
            "saldo_devedor_centavos": 0,
            "status": "pago",
            "data_pagamento": data_pag.isoformat(),
            "created_at": data_pag.isoformat(),
            "updated_at": data_pag.isoformat(),
            "usuario_id": context_id,
            "deleted": False
        }
        await db.parcelas.insert_one(parcela_quitacao)
        
        juros_periodo = 0
        ja_pago = 0
        valor_total_quitacao = capital
        valor_a_pagar = capital
        parcelas_canceladas = []
    else:
        # Regra de negócio (empréstimo aberto / apenas juros):
        # Ao QUITAR, a quitação corresponde ao CAPITAL + JUROS DO PERÍODO ATUAL.
        # A primeira parcela em aberto representa o período corrente; ela vira a
        # parcela final de quitação (capital + juros) e é marcada como PAGA.
        # As demais parcelas em aberto (geradas para períodos futuros) NÃO são
        # mais necessárias e são canceladas (soft-delete).
        parcela_quitacao = parcelas_abertas[0]
        juros_periodo = int(parcela_quitacao.get("valor_juros_centavos", 0) or 0)
        ja_pago = int(parcela_quitacao.get("valor_pago_centavos", 0) or 0)
        valor_total_quitacao = capital + juros_periodo
        valor_a_pagar = valor_total_quitacao - ja_pago
        numero_final = parcela_quitacao.get("numero_parcela")

        # 1. Transformar a parcela atual na parcela final (capital + juros) e quitá-la
        await db.parcelas.update_one(
            {"id": parcela_quitacao["id"], "usuario_id": context_id},
            {"$set": {
                "valor_principal_centavos": capital,
                "valor_juros_centavos": juros_periodo,
                "valor_total_centavos": valor_total_quitacao,
                "valor_pago_centavos": valor_total_quitacao,
                "saldo_devedor_centavos": 0,
                "status": "pago",
                "data_pagamento": data_pag.isoformat(),
                "updated_at": data_pag.isoformat(),
            }}
        )

        # 2. Cancelar (soft-delete) as demais parcelas futuras em aberto
        parcelas_canceladas = [p["id"] for p in parcelas_abertas[1:]]
        if parcelas_canceladas:
            await db.parcelas.update_many(
                {"id": {"$in": parcelas_canceladas}, "usuario_id": context_id},
                {"$set": {
                    "deleted": True,
                    "deleted_at": data_pag.isoformat(),
                    "deleted_motivo": "Empréstimo quitado — parcela futura não necessária",
                }}
            )

    # 3. Registrar o pagamento da quitação no histórico financeiro
    if valor_a_pagar > 0:
        cliente = await db.clientes.find_one({"id": emprestimo.get("cliente_id")}, {"_id": 0})
        pagamento_doc = {
            "id": str(_uuid.uuid4()),
            "parcela_id": parcela_quitacao["id"],
            "emprestimo_id": emprestimo_id,
            "tipo": "quitacao",
            "data_pagamento": data_pag.isoformat(),
            "valor_pago_centavos": valor_a_pagar,
            "metodo_pagamento": "dinheiro",
            "observacoes": "Quitação do empréstimo (capital + juros do período)",
            "created_at": data_pag.isoformat(),
            "usuario_id": context_id,
            "created_by": current_user.email,
            "cliente_id": emprestimo.get("cliente_id"),
            "cliente_nome": (cliente or {}).get("nome") or emprestimo.get("cliente_nome"),
            "cliente_telefone": (cliente or {}).get("telefone"),
            "valor_emprestimo_centavos": capital,
            "numero_parcela": numero_final,
            "deleted": False,
        }
        await db.pagamentos.insert_one(pagamento_doc)

    # 4. Atualizar total_parcelas das parcelas ativas e recalcular totais
    await db.parcelas.update_many(
        {"emprestimo_id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"$set": {"total_parcelas": numero_final}}
    )

    todas_parcelas = await db.parcelas.find(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
        },
        {"_id": 0}
    ).to_list(1000)

    valor_total_com_juros_centavos = sum(p.get("valor_total_centavos", 0) for p in todas_parcelas)
    valor_total_juros_centavos = valor_total_com_juros_centavos - capital

    # 5. Marcar empréstimo como quitado
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": {
            "status": "quitado",
            "valor_total_com_juros_centavos": valor_total_com_juros_centavos,
            "valor_total_juros_centavos": valor_total_juros_centavos,
            "prazo_meses": numero_final,
        }}
    )

    # 6. Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="QUITAR_EMPRESTIMO_ABERTO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Quitação empréstimo aberto: capital R$ {formatar_reais(capital)} + juros R$ {formatar_reais(juros_periodo)} = R$ {formatar_reais(valor_total_quitacao)} (parcela #{numero_final}). {len(parcelas_canceladas)} parcela(s) futura(s) cancelada(s).",
        dados_novos={
            "parcela_quitacao": numero_final,
            "valor_total_quitacao_centavos": valor_total_quitacao,
            "valor_pago_centavos": valor_a_pagar,
            "parcelas_canceladas": len(parcelas_canceladas),
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return {
        "message": "Empréstimo quitado com sucesso",
        "parcela_numero": numero_final,
        "valor_total_centavos": valor_total_quitacao,
        "valor_pago_centavos": valor_a_pagar,
        "parcelas_canceladas": len(parcelas_canceladas),
        "total_parcelas": numero_final,
        "valor_total_emprestimo_centavos": valor_total_com_juros_centavos,
    }



@router.get("/{emprestimo_id}/compartilhar-pdf")
async def compartilhar_emprestimo_pdf(
    emprestimo_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera PDF com detalhes do empréstimo para compartilhar com cliente"""
    
    context_id = get_user_context(current_user)
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0})
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Buscar cliente
    cliente = await db.clientes.find_one({
        "id": emprestimo["cliente_id"]
    }, {"_id": 0})
    
    # Buscar parcelas
    # Primeiro tenta com filtro completo, depois simplificado
    parcelas_cursor = db.parcelas.find({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id
    }, {"_id": 0}).sort("numero_parcela", 1)
    parcelas = await parcelas_cursor.to_list(length=None)
    
    # Filtrar parcelas não deletadas (se o campo existir)
    parcelas = [p for p in parcelas if not p.get("deleted", False)]
    
    # Log para debug
    logger = get_logger("gestorcred.pdf")
    logger.info(f"PDF Empréstimo {emprestimo_id}: {len(parcelas)} parcelas encontradas")
    
    # Criar PDF em memória
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        topMargin=1.2*cm, 
        bottomMargin=1*cm,
        leftMargin=1.5*cm,
        rightMargin=1.5*cm
    )
    elements = []
    styles = getSampleStyleSheet()
    
    # Cores do tema
    PRIMARY_COLOR = colors.HexColor('#10b981')  # Verde Kredor
    SECONDARY_COLOR = colors.HexColor('#059669')
    DARK_COLOR = colors.HexColor('#1f2937')
    GRAY_COLOR = colors.HexColor('#6b7280')
    LIGHT_GRAY = colors.HexColor('#f3f4f6')
    
    # Estilos customizados melhorados
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=PRIMARY_COLOR,
        spaceAfter=2,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_header = ParagraphStyle(
        'SubtitleHeader',
        parent=styles['Normal'],
        fontSize=9,
        textColor=GRAY_COLOR,
        spaceAfter=10,
        alignment=TA_CENTER
    )
    
    section_title = ParagraphStyle(
        'SectionTitle',
        parent=styles['Heading2'],
        fontSize=11,
        textColor=DARK_COLOR,
        spaceAfter=4,
        spaceBefore=6,
        fontName='Helvetica-Bold',
        borderPadding=(6, 6, 6, 6),
        backColor=LIGHT_GRAY,
        leftIndent=8
    )
    
    # Cabeçalho com logo em texto
    elements.append(Paragraph("Kredor", header_style))
    elements.append(Paragraph("Sistema de Gestão de Empréstimos", subtitle_header))
    
    # Linha separadora
    line_data = [['', '']]
    line_table = Table(line_data, colWidths=[18*cm])
    line_table.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, PRIMARY_COLOR),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line_table)
    elements.append(Spacer(1, 0.4*cm))
    
    # Seção: Dados do Cliente
    elements.append(Paragraph("👤  Dados do Cliente", section_title))
    elements.append(Spacer(1, 0.2*cm))
    
    dados_cliente = [
        ['Nome:', cliente.get('nome', 'N/A')],
        ['CPF:', cliente.get('cpf', 'N/A')],
        ['Telefone:', cliente.get('telefone', 'N/A')],
        ['Email:', cliente.get('email', 'N/A')]
    ]
    
    table_cliente = Table(dados_cliente, colWidths=[4.5*cm, 13.5*cm])
    table_cliente.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY_COLOR),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK_COLOR),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(table_cliente)
    elements.append(Spacer(1, 0.3*cm))
    
    # Seção: Dados do Empréstimo
    elements.append(Paragraph("💰  Informações do Empréstimo", section_title))
    elements.append(Spacer(1, 0.3*cm))
    
    # Handle different field naming conventions
    data_inicio = emprestimo.get('data_inicio') or emprestimo.get('data_emprestimo') or emprestimo.get('created_at')
    if isinstance(data_inicio, str):
        data_inicio = datetime.fromisoformat(data_inicio).strftime('%d/%m/%Y')
    else:
        data_inicio = data_inicio.strftime('%d/%m/%Y')
    
    # Get tipo_juros/metodo_calculo with fallback
    tipo_juros_raw = emprestimo.get('metodo_calculo') or emprestimo.get('tipo_juros', '')
    tipo_juros_label = {
        'simples': 'Juros Simples',
        'composto': 'Juros Compostos',
        'compostos': 'Juros Compostos',
        'apenas_juros': 'Apenas Juros (Sem Prazo)',
        'tabela_price': 'Tabela Price',
        'price': 'Tabela Price',
        'sac': 'SAC'
    }.get(tipo_juros_raw, tipo_juros_raw or 'N/A')
    
    periodicidade = emprestimo.get('periodicidade', 'mensal')
    
    # Get taxa with fallback to different field names
    if periodicidade == 'mensal':
        taxa_valor = emprestimo.get('taxa_juros_mensal') or emprestimo.get('taxa_juros', 0)
        taxa_label = 'Taxa de Juros (mensal)'
    else:
        taxa_valor = emprestimo.get('taxa_juros_semanal') or emprestimo.get('taxa_juros', 0)
        taxa_label = 'Taxa de Juros (semanal)'
    
    # Get valor principal with fallback
    valor_principal_centavos = emprestimo.get('valor_principal_centavos') or emprestimo.get('valor_emprestimo_centavos', 0)
    
    # Get total parcelas with fallback
    total_parcelas = emprestimo.get('prazo_meses') or emprestimo.get('prazo_semanas') or emprestimo.get('numero_parcelas') or 'Indefinido'
    
    # Status com cor
    status_raw = emprestimo.get('status', 'N/A').upper()
    status_colors_map = {
        'ATIVO': PRIMARY_COLOR,
        'QUITADO': colors.HexColor('#059669'),
        'INADIMPLENTE': colors.HexColor('#dc2626'),
        'CANCELADO': GRAY_COLOR
    }
    status_color = status_colors_map.get(status_raw, DARK_COLOR)
    
    dados_emprestimo = [
        ['Data de Início:', data_inicio],
        ['Valor Emprestado:', f"R$ {formatar_reais(valor_principal_centavos)}"],
        [taxa_label, f"{taxa_valor:.2f}%"],
        ['Método de Cálculo:', tipo_juros_label],
        ['Total de Parcelas:', str(total_parcelas)],
    ]
    
    table_emprestimo = Table(dados_emprestimo, colWidths=[5*cm, 13*cm])
    table_emprestimo.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY_COLOR),
        ('TEXTCOLOR', (1, 0), (1, -1), DARK_COLOR),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('TOPPADDING', (0, 0), (-1, -1), 2),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(table_emprestimo)
    
    # Status em destaque
    status_data = [['Status:', status_raw]]
    status_table = Table(status_data, colWidths=[5*cm, 13*cm])
    status_table.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY_COLOR),
        ('TEXTCOLOR', (1, 0), (1, -1), status_color),
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'LEFT'),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
    ]))
    elements.append(status_table)
    elements.append(Spacer(1, 0.3*cm))
    
    # Seção: Tabela de Parcelas
    if parcelas:
        elements.append(Paragraph("📋  Detalhamento de Parcelas", section_title))
        elements.append(Spacer(1, 0.2*cm))
        
        table_data = [['#', 'Vencimento', 'Valor', 'Pago', 'Status']]
        
        for p in parcelas:
            venc = p.get('data_vencimento')
            if isinstance(venc, str):
                venc = datetime.fromisoformat(venc).strftime('%d/%m/%Y')
            else:
                venc = venc.strftime('%d/%m/%Y')
            
            status_map = {
                'pago': 'PAGO',
                'pendente': 'PENDENTE',
                'atrasado': 'ATRASADO',
                'parcial': 'PARCIAL'
            }
            
            table_data.append([
                f"{p.get('numero_parcela')}/{p.get('total_parcelas') or '∞'}",
                venc,
                f"R$ {formatar_reais(p.get('valor_total_centavos', 0))}",
                f"R$ {formatar_reais(p.get('valor_pago_centavos', 0))}",
                status_map.get(p.get('status'), p.get('status', 'N/A'))
            ])
        
        table_parcelas = Table(table_data, colWidths=[2.5*cm, 3.5*cm, 3.5*cm, 3.5*cm, 4.5*cm])
        
        # Estilo com cores alternadas nas linhas
        parcelas_style = [
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('BACKGROUND', (0, 0), (-1, 0), PRIMARY_COLOR),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), DARK_COLOR),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#d1d5db')),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
        ]
        
        # Adicionar cores alternadas para linhas
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                parcelas_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f9fafb')))
        
        # Colorir status
        for i, row in enumerate(table_data[1:], start=1):
            status = row[4]
            if status == 'PAGO':
                parcelas_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#059669')))
                parcelas_style.append(('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'))
            elif status == 'ATRASADO':
                parcelas_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#dc2626')))
                parcelas_style.append(('FONTNAME', (4, i), (4, i), 'Helvetica-Bold'))
            elif status == 'PENDENTE':
                parcelas_style.append(('TEXTCOLOR', (4, i), (4, i), colors.HexColor('#f59e0b')))
        
        table_parcelas.setStyle(TableStyle(parcelas_style))
        elements.append(table_parcelas)
        elements.append(Spacer(1, 0.3*cm))
    
    # Seção: Resumo Financeiro
    elements.append(Paragraph("💵  Resumo Financeiro", section_title))
    elements.append(Spacer(1, 0.2*cm))
    
    # Calcular totais corretamente
    total_a_pagar = sum(p.get('valor_total_centavos', 0) for p in parcelas)  # Soma de todas as parcelas
    total_pago = sum(p.get('valor_pago_centavos', 0) for p in parcelas)  # Total já pago
    total_devido = total_a_pagar - total_pago  # Saldo pendente
    total_juros = total_a_pagar - valor_principal_centavos  # Total de juros
    
    # Box com resumo financeiro destacado
    dados_totais = [
        ['Total Emprestado:', f"R$ {formatar_reais(valor_principal_centavos)}"],
        ['Total de Juros:', f"R$ {formatar_reais(total_juros)}"],
        ['Total a Pagar:', f"R$ {formatar_reais(total_a_pagar)}"],
        ['Total Pago:', f"R$ {formatar_reais(total_pago)}"],
        ['Saldo Pendente:', f"R$ {formatar_reais(total_devido)}"],
    ]
    
    table_totais = Table(dados_totais, colWidths=[9*cm, 9*cm])
    table_totais.setStyle(TableStyle([
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (0, -1), DARK_COLOR),
        ('TEXTCOLOR', (1, 0), (1, 0), DARK_COLOR),  # Total Emprestado
        ('TEXTCOLOR', (1, 1), (1, 1), colors.HexColor('#f59e0b')),  # Total de Juros (laranja)
        ('TEXTCOLOR', (1, 2), (1, 2), DARK_COLOR),  # Total a Pagar
        ('TEXTCOLOR', (1, 3), (1, 3), colors.HexColor('#059669')),  # Total Pago (verde)
        ('TEXTCOLOR', (1, 4), (1, 4), colors.HexColor('#dc2626') if total_devido > 0 else colors.HexColor('#059669')),  # Saldo Pendente
        ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
        ('ALIGN', (1, 0), (1, -1), 'RIGHT'),
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT_GRAY),
        ('BOX', (0, 0), (-1, -1), 1.5, PRIMARY_COLOR),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#d1d5db')),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
    ]))
    elements.append(table_totais)
    
    # Rodapé melhorado
    elements.append(Spacer(1, 0.5*cm))
    
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=7,
        textColor=GRAY_COLOR,
        alignment=TA_CENTER,
        spaceAfter=2
    )
    
    footer_text = f"<b>Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')}</b>"
    elements.append(Paragraph(footer_text, footer_style))
    
    elements.append(Paragraph("Kredor - Sistema de Gestão de Empréstimos", footer_style))
    elements.append(Paragraph("Este documento é confidencial e destinado exclusivamente ao cliente mencionado.", footer_style))
    
    # Gerar PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="GERAR_PDF_EMPRESTIMO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Gerou PDF do empréstimo para {cliente.get('nome', 'cliente')}",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Nome arquivo
    cliente_nome_safe = cliente.get('nome', 'cliente').replace(' ', '_')[:30]
    filename = f"emprestimo_{cliente_nome_safe}_{emprestimo_id[:8]}.pdf"
    
    return StreamingResponse(
        buffer,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f"attachment; filename={filename}"
        }
    )


@router.get("/{emprestimo_id}/recibo-quitacao")
async def recibo_quitacao_pdf(
    emprestimo_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera o Recibo de Quitação (PDF) de um empréstimo quitado."""

    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    if emprestimo.get("status") != "quitado":
        raise HTTPException(
            status_code=400,
            detail="O recibo de quitação só está disponível para empréstimos quitados."
        )

    cliente = await db.clientes.find_one({"id": emprestimo.get("cliente_id")}, {"_id": 0}) or {}

    # Pagamentos do empréstimo (exclui deletados)
    pagamentos = await db.pagamentos.find(
        {"emprestimo_id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0}
    ).to_list(1000)

    total_pago = sum(int(p.get("valor_pago_centavos", 0) or 0) for p in pagamentos)

    # Data de quitação: pagamento de quitação mais recente, senão último pagamento
    def _parse_dt(v):
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

    quitacao_pgtos = [p for p in pagamentos if p.get("tipo") == "quitacao" and p.get("data_pagamento")]
    if quitacao_pgtos:
        data_quitacao = max(_parse_dt(p["data_pagamento"]) for p in quitacao_pgtos if _parse_dt(p["data_pagamento"]))
    else:
        datas = [_parse_dt(p.get("data_pagamento")) for p in pagamentos if _parse_dt(p.get("data_pagamento"))]
        data_quitacao = max(datas) if datas else datetime.now(timezone.utc)

    capital = int(emprestimo.get("valor_principal_centavos", 0) or 0)
    total_juros = total_pago - capital
    if total_juros < 0:
        total_juros = int(emprestimo.get("valor_total_juros_centavos", 0) or 0)

    def fmt_moeda(centavos):
        return f"R$ {formatar_reais(centavos)}"

    def fmt_data(dt):
        if isinstance(dt, str):
            dt = _parse_dt(dt)
        return dt.strftime("%d/%m/%Y") if dt else "-"

    # Construir PDF
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    elements = []
    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor('#10b981')
    DARK = colors.HexColor('#1f2937')
    GRAY = colors.HexColor('#6b7280')
    LIGHT = colors.HexColor('#f3f4f6')

    header_style = ParagraphStyle('H', parent=styles['Heading1'], fontSize=22,
                                  textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=2,
                                  fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, textColor=GRAY,
                               alignment=TA_CENTER, spaceAfter=12)
    section = ParagraphStyle('Sec', parent=styles['Heading2'], fontSize=11, textColor=DARK,
                             spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold',
                             backColor=LIGHT, borderPadding=(6, 6, 6, 6), leftIndent=6)
    decl = ParagraphStyle('Decl', parent=styles['Normal'], fontSize=11, textColor=DARK,
                          alignment=TA_LEFT, leading=18, spaceBefore=8)

    elements.append(Paragraph("RECIBO DE QUITAÇÃO", header_style))
    elements.append(Paragraph("Kredor - Sistema de Gestão de Empréstimos", sub_style))

    line = Table([['', '']], colWidths=[17 * cm])
    line.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Dados do Cliente", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_cliente = [
        ['Nome:', cliente.get('nome', 'N/A')],
        ['CPF/CNPJ:', cliente.get('cpf_cnpj') or cliente.get('cpf') or 'N/A'],
        ['Telefone:', cliente.get('telefone', 'N/A')],
    ]
    tc = Table(dados_cliente, colWidths=[4 * cm, 13 * cm])
    tc.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(tc)
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph("Resumo da Quitação", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_quit = [
        ['Contrato:', f"#{emprestimo_id[:8].upper()}"],
        ['Data de Início:', fmt_data(emprestimo.get('data_inicio'))],
        ['Data de Quitação:', fmt_data(data_quitacao)],
        ['Capital Emprestado:', fmt_moeda(capital)],
        ['Total de Juros:', fmt_moeda(total_juros)],
        ['VALOR TOTAL PAGO:', fmt_moeda(total_pago)],
    ]
    tq = Table(dados_quit, colWidths=[6 * cm, 11 * cm])
    tq.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 5), (-1, 5), LIGHT),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 5), (-1, 5), 12),
        ('TEXTCOLOR', (1, 5), (1, 5), PRIMARY),
    ]))
    elements.append(tq)
    elements.append(Spacer(1, 0.5 * cm))

    texto = (
        f"Declaro, para os devidos fins, que <b>{cliente.get('nome', 'o cliente')}</b> "
        f"efetuou o pagamento integral do empréstimo de contrato <b>#{emprestimo_id[:8].upper()}</b>, "
        f"no valor total de <b>{fmt_moeda(total_pago)}</b> (capital de {fmt_moeda(capital)} "
        f"acrescido de {fmt_moeda(total_juros)} de juros), encontrando-se o referido empréstimo "
        f"<b>TOTALMENTE QUITADO</b> nesta data, nada mais havendo a cobrar."
    )
    elements.append(Paragraph(texto, decl))
    elements.append(Spacer(1, 1.5 * cm))

    assinatura = Table(
        [['_' * 40], [f"{current_user.nome if getattr(current_user, 'nome', None) else 'Credor'}"]],
        colWidths=[10 * cm]
    )
    assinatura.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (0, 1), 9), ('TEXTCOLOR', (0, 1), (0, 1), GRAY),
        ('TOPPADDING', (0, 1), (0, 1), 2),
    ]))
    elements.append(assinatura)
    elements.append(Spacer(1, 0.8 * cm))

    footer = ParagraphStyle('F', parent=styles['Normal'], fontSize=7, textColor=GRAY,
                            alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} - Kredor", footer))

    doc.build(elements)
    buffer.seek(0)

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="GERAR_RECIBO_QUITACAO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Gerou recibo de quitação para {cliente.get('nome', 'cliente')} - {fmt_moeda(total_pago)}",
        ip=None
    )

    nome_safe = (cliente.get('nome', 'cliente') or 'cliente').replace(' ', '_')[:30]
    filename = f"recibo_quitacao_{nome_safe}_{emprestimo_id[:8]}.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )





@router.get("/{emprestimo_id}/ajustes")
async def listar_ajustes_emprestimo(
    emprestimo_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Lista os ajustes de capital (amortizações e incorporações de juros) de um
    empréstimo, em ordem cronológica (mais recente primeiro), para a timeline.
    """
    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"_id": 0, "id": 1}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    docs = await db.pagamentos.find(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "tipo": {"$in": ["amortizacao", "incorporacao_juros"]},
        },
        {"_id": 0}
    ).to_list(1000)

    ajustes = []
    for d in docs:
        tipo = d.get("tipo")
        valor = d.get("valor_pago_centavos", 0) if tipo == "amortizacao" else d.get("valor_incorporado_centavos", 0)
        ajustes.append({
            "id": d.get("id"),
            "tipo": tipo,
            "data": d.get("data_pagamento") or d.get("created_at"),
            "valor_centavos": int(valor or 0),
            "principal_anterior_centavos": d.get("principal_anterior_centavos"),
            "principal_apos_centavos": d.get("principal_apos_centavos"),
            "metodo_pagamento": d.get("metodo_pagamento"),
            "observacoes": d.get("observacoes"),
            "created_by": d.get("created_by"),
        })

    # Ordenar por data desc (strings ISO ordenam corretamente)
    ajustes.sort(key=lambda a: str(a.get("data") or ""), reverse=True)
    return {"ajustes": ajustes, "total": len(ajustes)}


def _build_recibo_amortizacao_pdf(emprestimo_id, emprestimo, pagamento, cliente, credor_nome):
    """Monta o PDF do comprovante de amortização e retorna um io.BytesIO."""

    def _parse_dt(v):
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

    def fmt_moeda(centavos):
        return f"R$ {formatar_reais(centavos)}"

    def fmt_data(dt):
        if isinstance(dt, str):
            dt = _parse_dt(dt)
        return dt.strftime("%d/%m/%Y") if dt else "-"

    valor_amort = int(pagamento.get("valor_pago_centavos", 0) or 0)
    principal_anterior_centavos = int(pagamento.get("principal_anterior_centavos", 0) or 0)
    principal_apos_centavos = pagamento.get("principal_apos_centavos")
    if principal_apos_centavos is None:
        principal_apos_centavos = principal_anterior_centavos - valor_amort
    principal_apos_centavos = int(principal_apos_centavos)
    data_amort = pagamento.get("data_pagamento") or pagamento.get("created_at")
    metodo = (pagamento.get("metodo_pagamento") or "").upper()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    elements = []
    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor('#10b981')
    DARK = colors.HexColor('#1f2937')
    GRAY = colors.HexColor('#6b7280')
    LIGHT = colors.HexColor('#f3f4f6')

    header_style = ParagraphStyle('H', parent=styles['Heading1'], fontSize=22,
                                  textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=2,
                                  fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, textColor=GRAY,
                               alignment=TA_CENTER, spaceAfter=12)
    section = ParagraphStyle('Sec', parent=styles['Heading2'], fontSize=11, textColor=DARK,
                             spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold',
                             backColor=LIGHT, borderPadding=(6, 6, 6, 6), leftIndent=6)
    decl = ParagraphStyle('Decl', parent=styles['Normal'], fontSize=11, textColor=DARK,
                          alignment=TA_LEFT, leading=18, spaceBefore=8)

    elements.append(Paragraph("COMPROVANTE DE AMORTIZAÇÃO", header_style))
    elements.append(Paragraph("Kredor - Sistema de Gestão de Empréstimos", sub_style))

    line = Table([['', '']], colWidths=[17 * cm])
    line.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Dados do Cliente", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_cliente = [
        ['Nome:', cliente.get('nome', 'N/A')],
        ['CPF/CNPJ:', cliente.get('cpf_cnpj') or cliente.get('cpf') or 'N/A'],
        ['Telefone:', cliente.get('telefone', 'N/A')],
    ]
    tc = Table(dados_cliente, colWidths=[4 * cm, 13 * cm])
    tc.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(tc)
    elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph("Detalhes da Amortização", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_amort = [
        ['Contrato:', f"#{emprestimo_id[:8].upper()}"],
        ['Data da Amortização:', fmt_data(data_amort)],
        ['Forma de Pagamento:', metodo or 'N/A'],
        ['Capital Anterior:', fmt_moeda(principal_anterior_centavos)],
        ['Valor Amortizado:', fmt_moeda(valor_amort)],
        ['NOVO CAPITAL:', fmt_moeda(principal_apos_centavos)],
    ]
    ta = Table(dados_amort, colWidths=[6 * cm, 11 * cm])
    ta.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
        ('BACKGROUND', (0, 5), (-1, 5), LIGHT),
        ('FONTNAME', (0, 5), (-1, 5), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 5), (-1, 5), 12),
        ('TEXTCOLOR', (1, 5), (1, 5), PRIMARY),
    ]))
    elements.append(ta)
    elements.append(Spacer(1, 0.5 * cm))

    texto = (
        f"Declaro, para os devidos fins, que recebi de <b>{cliente.get('nome', 'o cliente')}</b> "
        f"o valor de <b>{fmt_moeda(valor_amort)}</b> a título de amortização de capital do empréstimo "
        f"de contrato <b>#{emprestimo_id[:8].upper()}</b>. Após esta amortização, o saldo devedor de "
        f"capital passou de {fmt_moeda(principal_anterior_centavos)} para <b>{fmt_moeda(principal_apos_centavos)}</b>."
    )
    elements.append(Paragraph(texto, decl))
    elements.append(Spacer(1, 1.5 * cm))

    assinatura = Table(
        [['_' * 40], [f"{credor_nome or 'Credor'}"]],
        colWidths=[10 * cm]
    )
    assinatura.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (0, 1), 9), ('TEXTCOLOR', (0, 1), (0, 1), GRAY),
        ('TOPPADDING', (0, 1), (0, 1), 2),
    ]))
    elements.append(assinatura)
    elements.append(Spacer(1, 0.8 * cm))

    footer = ParagraphStyle('F', parent=styles['Normal'], fontSize=7, textColor=GRAY,
                            alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} - Kredor", footer))

    doc.build(elements)
    buffer.seek(0)
    return buffer


@router.get("/{emprestimo_id}/recibo-amortizacao/{pagamento_id}")
async def recibo_amortizacao_pdf(
    emprestimo_id: str,
    pagamento_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera o Comprovante de Amortização de Capital (PDF) para enviar ao cliente."""
    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    pagamento = await db.pagamentos.find_one(
        {"id": pagamento_id, "emprestimo_id": emprestimo_id, "usuario_id": context_id,
         "tipo": "amortizacao", "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Amortização não encontrada")

    cliente = await db.clientes.find_one({"id": emprestimo.get("cliente_id")}, {"_id": 0}) or {}
    credor_nome = getattr(current_user, 'nome', None)
    buffer = _build_recibo_amortizacao_pdf(emprestimo_id, emprestimo, pagamento, cliente, credor_nome)

    nome_safe = (cliente.get('nome', 'cliente') or 'cliente').replace(' ', '_')[:30]
    filename = f"comprovante_amortizacao_{nome_safe}_{emprestimo_id[:8]}.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{emprestimo_id}/recibo-amortizacao/{pagamento_id}/whatsapp")
async def enviar_recibo_amortizacao_whatsapp(
    emprestimo_id: str,
    pagamento_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Envia o comprovante de amortização (PDF) ao cliente via WhatsApp (Evolution API)."""

    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    pagamento = await db.pagamentos.find_one(
        {"id": pagamento_id, "emprestimo_id": emprestimo_id, "usuario_id": context_id,
         "tipo": "amortizacao", "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not pagamento:
        raise HTTPException(status_code=404, detail="Amortização não encontrada")

    cliente = await db.clientes.find_one({"id": emprestimo.get("cliente_id")}, {"_id": 0}) or {}
    telefone = cliente.get("telefone") or cliente.get("celular")
    if not telefone:
        raise HTTPException(status_code=400, detail="Cliente não possui telefone cadastrado")

    credor_nome = getattr(current_user, 'nome', None)
    buffer = _build_recibo_amortizacao_pdf(emprestimo_id, emprestimo, pagamento, cliente, credor_nome)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    def fmt_moeda(centavos):
        return f"R$ {formatar_reais(centavos)}"

    valor_amort = int(pagamento.get("valor_pago_centavos", 0) or 0)
    legenda = (
        f"Olá {cliente.get('nome', '')}! Segue o comprovante da amortização de "
        f"{fmt_moeda(valor_amort)} referente ao seu empréstimo. Obrigado!"
    )
    nome_safe = (cliente.get('nome', 'cliente') or 'cliente').replace(' ', '_')[:30]
    filename = f"comprovante_amortizacao_{nome_safe}.pdf"

    resultado = await enviar_documento_whatsapp(
        usuario_id=context_id,
        numero_destino=telefone,
        base64_documento=b64,
        nome_arquivo=filename,
        legenda=legenda,
    )

    if not resultado.get("success"):
        err = resultado.get("error")
        msg = resultado.get("message", "Falha ao enviar pelo WhatsApp")
        if err == "whatsapp_nao_conectado":
            msg = "WhatsApp não está conectado. Conecte sua conta em Configurações › WhatsApp."
        elif err == "evolution_nao_configurada":
            msg = "Integração de WhatsApp não configurada. Configure a Evolution API primeiro."
        raise HTTPException(status_code=400, detail=msg)

    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="ENVIAR_RECIBO_WHATSAPP",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Enviou comprovante de amortização ({fmt_moeda(valor_amort)}) via WhatsApp para {cliente.get('nome', 'cliente')}",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return {"success": True, "message": "Comprovante enviado pelo WhatsApp", "numero": resultado.get("numero_enviado")}


@router.post("/{emprestimo_id}/ajustes/{pagamento_id}/estornar")
async def estornar_ajuste(
    emprestimo_id: str,
    pagamento_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Estorna (reverte) um ajuste de capital lançado por engano.

    - amortizacao: devolve o valor amortizado ao capital (novo = atual + valor).
      Se o empréstimo havia sido quitado por esta amortização total, reativa (ativo)
      e restaura as parcelas canceladas pela quitação.
    - incorporacao_juros: remove do capital o valor incorporado (novo = atual - valor),
      desde que o resultado não fique negativo.
    O documento do ajuste é marcado como estornado (soft-delete).
    """
    if not is_owner(current_user):
        raise HTTPException(status_code=403, detail="Acesso restrito ao dono da conta.")

    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    ajuste = await db.pagamentos.find_one(
        {"id": pagamento_id, "emprestimo_id": emprestimo_id, "usuario_id": context_id,
         "tipo": {"$in": ["amortizacao", "incorporacao_juros"]}, "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not ajuste:
        raise HTTPException(status_code=404, detail="Ajuste não encontrado ou já estornado")

    tipo = ajuste.get("tipo")
    valor_atual = int(emprestimo.get("valor_principal_centavos", 0) or 0)

    if tipo == "amortizacao":
        valor = int(ajuste.get("valor_pago_centavos", 0) or 0)
        novo_principal = valor_atual + valor
    else:  # incorporacao_juros
        valor = int(ajuste.get("valor_incorporado_centavos", 0) or 0)
        novo_principal = valor_atual - valor
        if novo_principal < 0:
            raise HTTPException(
                status_code=400,
                detail=f"Não é possível estornar: o capital ficaria negativo (atual R$ {formatar_reais(valor_atual)}, incorporado R$ {formatar_reais(valor)})."
            )

    # 1. Reverter o capital
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": {"valor_principal_centavos": novo_principal}}
    )

    # 2. Se estava quitado (amortização total), reativar e restaurar parcelas canceladas
    reativado = False
    if tipo == "amortizacao" and emprestimo.get("status") == "quitado":
        await db.emprestimos.update_one(
            {"id": emprestimo_id, "usuario_id": context_id},
            {"$set": {"status": "ativo"}}
        )
        await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": True,
                "deleted_motivo": "Capital quitado por amortização total",
            },
            {"$set": {"deleted": False}, "$unset": {"deleted_at": "", "deleted_motivo": ""}}
        )
        reativado = True

    # 3. Recalcular juros das parcelas em aberto com o novo capital (apenas_juros)
    periodicidade = emprestimo.get("periodicidade", "mensal")
    taxa_juros = (emprestimo.get("taxa_juros_semanal") if periodicidade == "semanal"
                  else emprestimo.get("taxa_juros_mensal")) or 0
    novo_juros = arredondar_centavos(novo_principal * (taxa_juros / 100))
    await db.parcelas.update_many(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado"]},
            "valor_pago_centavos": 0,
        },
        {"$set": {"valor_juros_centavos": novo_juros, "valor_total_centavos": novo_juros, "saldo_devedor_centavos": novo_principal}}
    )
    await db.parcelas.update_many(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": context_id,
            "deleted": {"$ne": True},
            "status": {"$in": ["pendente", "atrasado", "parcial"]},
        },
        {"$set": {"saldo_devedor_centavos": novo_principal}}
    )

    # 4. Marcar o ajuste como estornado (soft-delete)
    await db.pagamentos.update_one(
        {"id": pagamento_id, "usuario_id": context_id},
        {"$set": {
            "deleted": True,
            "deleted_at": datetime.now(timezone.utc).isoformat(),
            "deleted_by": current_user.email,
            "estornado": True,
        }}
    )

    # 5. Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="ESTORNAR_AJUSTE",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Estorno de {tipo} de R$ {formatar_reais(valor)}. Capital {formatar_reais(valor_atual)} -> {formatar_reais(novo_principal)}. Reativado: {reativado}",
        dados_anteriores={"valor_principal_centavos": valor_atual},
        dados_novos={"valor_principal_centavos": novo_principal, "reativado": reativado},
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return {
        "success": True,
        "message": "Ajuste estornado com sucesso",
        "tipo": tipo,
        "valor_estornado_centavos": valor,
        "principal_anterior_centavos": valor_atual,
        "principal_atual_centavos": novo_principal,
        "reativado": reativado,
    }


@router.post("/{emprestimo_id}/amortizar")
async def amortizar_capital(
    emprestimo_id: str,
    payload: AmortizacaoRequest,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Amortiza capital de um empréstimo aberto (sem prazo + apenas_juros)
    
    - Reduz valor_principal_centavos do empréstimo
    - Registra um pagamento do tipo "amortizacao"
    - Se recalcular_juros=True: recalcula valor_juros_centavos/valor_total_centavos das parcelas
      pendentes, atrasadas e parciais com base no novo principal
    - Se capital chegar a 0: marca empréstimo como quitado e cancela parcelas pendentes
    """
    context_id = get_user_context(current_user)
    
    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    if not emprestimo.get("sem_prazo"):
        raise HTTPException(
            status_code=400,
            detail="Amortização só é aplicável a empréstimos sem prazo (modalidade apenas_juros)"
        )
    if emprestimo.get("status") != "ativo":
        raise HTTPException(status_code=400, detail="Empréstimo não está ativo")
    
    valor_atual = int(emprestimo.get("valor_principal_centavos", 0))
    valor_amort = payload.valor_amortizacao_centavos
    
    if valor_amort > valor_atual:
        raise HTTPException(
            status_code=400,
            detail=f"Valor da amortização (R$ {formatar_reais(valor_amort)}) maior que o capital devido (R$ {formatar_reais(valor_atual)})"
        )
    
    novo_principal = valor_atual - valor_amort
    data_pag = payload.data_pagamento or datetime.now(timezone.utc)
    
    # Amortização: capital, movimento e parcelas mudam juntos ou não mudam.
    async with transacao() as sessao:
        # 1. Atualizar valor_principal_centavos do empréstimo
        await db.emprestimos.update_one(
            {"id": emprestimo_id, "usuario_id": context_id},
            {"$set": {"valor_principal_centavos": novo_principal}},
            session=sessao,
        )
    
        # 2. Registrar amortização como pagamento (tipo='amortizacao')
        amort_doc = {
            "id": str(_uuid.uuid4()),
            "parcela_id": None,
            "emprestimo_id": emprestimo_id,
            "tipo": "amortizacao",
            "data_pagamento": data_pag.isoformat() if isinstance(data_pag, datetime) else data_pag,
            "valor_pago_centavos": valor_amort,
            "metodo_pagamento": payload.metodo_pagamento,
            "observacoes": payload.observacoes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "usuario_id": context_id,
            "created_by": current_user.email,
            "cliente_id": emprestimo.get("cliente_id"),
            "cliente_nome": emprestimo.get("cliente_nome"),
            "valor_emprestimo_centavos": valor_atual,
            "principal_anterior_centavos": valor_atual,
            "principal_apos_centavos": novo_principal,
        }
        await db.pagamentos.insert_one(amort_doc, session=sessao)
    
        # 3. Recalcular juros das parcelas pendentes se solicitado
        parcelas_atualizadas = 0
        if payload.recalcular_juros and novo_principal > 0:
            periodicidade = emprestimo.get("periodicidade", "mensal")
            if periodicidade == "semanal":
                taxa_juros = emprestimo.get("taxa_juros_semanal", 0) or 0
            else:
                taxa_juros = emprestimo.get("taxa_juros_mensal", 0) or 0
        
            novo_juros = arredondar_centavos(novo_principal * (taxa_juros / 100))
        
            result_upd = await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado", "parcial"]},
                    "valor_pago_centavos": 0,  # só recalcular as que ainda nao tem pagamento parcial
                },
                {"$set": {
                    "valor_juros_centavos": novo_juros,
                    "valor_total_centavos": novo_juros,
                    "saldo_devedor_centavos": novo_principal,
                }},
                session=sessao,
            )
            parcelas_atualizadas = result_upd.modified_count
        
            # Atualizar saldo_devedor_centavos das demais (parciais ou nao zeradas) tambem
            await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado", "parcial"]},
                },
                {"$set": {"saldo_devedor_centavos": novo_principal}},
                session=sessao,
            )
        else:
            # Mesmo sem recalcular juros, atualiza saldo_devedor_centavos (informativo)
            await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado", "parcial"]},
                },
                {"$set": {"saldo_devedor_centavos": novo_principal}},
                session=sessao,
            )
    
        # 4. Se capital chegou a zero -> quitar empréstimo
        quitado = False
        if novo_principal <= 0:
            # Soft-cancel parcelas pendentes/atrasadas/parciais
            await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado", "parcial"]},
                },
                {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat(), "deleted_motivo": "Capital quitado por amortização total"}},
                session=sessao,
            )
            await db.emprestimos.update_one(
                {"id": emprestimo_id, "usuario_id": context_id},
                {"$set": {"status": "quitado"}},
                session=sessao,
            )
            quitado = True
    
    # 5. Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="AMORTIZAR_CAPITAL",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Amortização de R$ {formatar_reais(valor_amort)} no capital. {formatar_reais(valor_atual)} -> {formatar_reais(novo_principal)}. Recalcular: {payload.recalcular_juros}",
        dados_anteriores={"valor_principal_centavos": valor_atual},
        dados_novos={
            "valor_principal_centavos": novo_principal,
            "valor_amortizado_centavos": valor_amort,
            "recalculou_juros": payload.recalcular_juros,
            "parcelas_atualizadas": parcelas_atualizadas,
            "quitado": quitado,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "message": "Amortização registrada com sucesso",
        "valor_amortizado_centavos": valor_amort,
        "principal_anterior_centavos": valor_atual,
        "principal_atual_centavos": novo_principal,
        "recalculou_juros": payload.recalcular_juros,
        "parcelas_atualizadas": parcelas_atualizadas,
        "quitado": quitado,
    }


@router.post("/{emprestimo_id}/incorporar-juros")
async def incorporar_juros(
    emprestimo_id: str,
    payload: IncorporacaoJurosRequest,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Incorpora juros (não pagos) ao capital de um empréstimo aberto (sem prazo).

    Operação MANUAL: o usuário decide quanto de juros somar ao capital.
    - Aumenta valor_principal_centavos do empréstimo (novo = atual + valor_juros_centavos)
    - NÃO conta como recebimento (valor_pago_centavos = 0 no histórico)
    - Se baixar_parcelas=True: quita as parcelas de juros em aberto (pendente/atrasado/parcial)
      por ordem de vencimento, até consumir o valor incorporado
    - Se recalcular_juros=True: recalcula juros das próximas parcelas pendentes com o novo capital
    """
    context_id = get_user_context(current_user)

    emprestimo = await db.emprestimos.find_one(
        {"id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}},
        {"_id": 0}
    )
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    if not emprestimo.get("sem_prazo"):
        raise HTTPException(
            status_code=400,
            detail="Incorporação de juros só é aplicável a empréstimos sem prazo (modalidade Apenas Juros)"
        )
    if emprestimo.get("status") != "ativo":
        raise HTTPException(status_code=400, detail="Empréstimo não está ativo")

    valor_atual = int(emprestimo.get("valor_principal_centavos", 0))
    valor_juros_centavos = payload.valor_juros_centavos
    if valor_juros_centavos <= 0:
        raise HTTPException(status_code=400, detail="Informe um valor de juros válido para incorporar")

    novo_principal = valor_atual + valor_juros_centavos
    data_inc = payload.data_incorporacao or datetime.now(timezone.utc)

    # Incorporação: capital, movimento, baixas e recálculo mudam juntos ou não mudam.
    async with transacao() as sessao:
        # 1. Aumentar o capital do empréstimo
        await db.emprestimos.update_one(
            {"id": emprestimo_id, "usuario_id": context_id},
            {"$set": {"valor_principal_centavos": novo_principal}},
            session=sessao,
        )

        # 2. Registrar movimento (tipo='incorporacao_juros'). valor_pago_centavos=0 -> NÃO conta como receita.
        inc_doc = {
            "id": str(_uuid.uuid4()),
            "parcela_id": None,
            "emprestimo_id": emprestimo_id,
            "tipo": "incorporacao_juros",
            "data_pagamento": data_inc.isoformat() if isinstance(data_inc, datetime) else data_inc,
            "valor_pago_centavos": 0,
            "valor_incorporado_centavos": valor_juros_centavos,
            "metodo_pagamento": "incorporacao",
            "observacoes": payload.observacoes,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "usuario_id": context_id,
            "created_by": current_user.email,
            "cliente_id": emprestimo.get("cliente_id"),
            "cliente_nome": emprestimo.get("cliente_nome"),
            "valor_emprestimo_centavos": valor_atual,
            "principal_anterior_centavos": valor_atual,
            "principal_apos_centavos": novo_principal,
        }
        await db.pagamentos.insert_one(inc_doc, session=sessao)

        # 3. Baixar parcelas de juros em aberto (por ordem de vencimento) até consumir o valor
        parcelas_baixadas = 0
        if payload.baixar_parcelas:
            restante = valor_juros_centavos
            parcelas_abertas = await db.parcelas.find(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado", "parcial"]},
                },
                {"_id": 0},
                session=sessao,
            ).sort("data_vencimento", 1).to_list(1000)

            for parc in parcelas_abertas:
                if restante <= 0:
                    break
                devido = (
                    (parc.get("valor_total_centavos", 0) or 0)
                    - (parc.get("valor_pago_centavos", 0) or 0)
                    + (parc.get("valor_multa_centavos", 0) or 0)
                    + (parc.get("valor_juros_mora_centavos", 0) or 0)
                )
                if devido <= 0:
                    continue
                if restante >= devido:
                    # Baixa integral da parcela via incorporação
                    await db.parcelas.update_one(
                        {"id": parc["id"], "usuario_id": context_id},
                        {"$set": {
                            "status": "pago",
                            "valor_pago_centavos": (parc.get("valor_pago_centavos", 0) or 0) + devido,
                            "data_pagamento": data_inc.isoformat() if isinstance(data_inc, datetime) else data_inc,
                            "incorporado": True,
                        }},
                        session=sessao,
                    )
                    restante = restante - devido
                    parcelas_baixadas += 1
                else:
                    # Baixa parcial da parcela
                    await db.parcelas.update_one(
                        {"id": parc["id"], "usuario_id": context_id},
                        {"$set": {
                            "status": "parcial",
                            "valor_pago_centavos": (parc.get("valor_pago_centavos", 0) or 0) + restante,
                            "incorporado": True,
                        }},
                        session=sessao,
                    )
                    restante = 0

        # 4. Recalcular juros das próximas parcelas pendentes com o novo capital
        parcelas_atualizadas = 0
        periodicidade = emprestimo.get("periodicidade", "mensal")
        if periodicidade == "semanal":
            taxa_juros = emprestimo.get("taxa_juros_semanal", 0) or 0
        else:
            taxa_juros = emprestimo.get("taxa_juros_mensal", 0) or 0
        novo_juros_parcela = arredondar_centavos(novo_principal * (taxa_juros / 100))

        if payload.recalcular_juros:
            result_upd = await db.parcelas.update_many(
                {
                    "emprestimo_id": emprestimo_id,
                    "usuario_id": context_id,
                    "deleted": {"$ne": True},
                    "status": {"$in": ["pendente", "atrasado"]},
                    "valor_pago_centavos": 0,
                },
                {"$set": {
                    "valor_juros_centavos": novo_juros_parcela,
                    "valor_total_centavos": novo_juros_parcela,
                    "saldo_devedor_centavos": novo_principal,
                }},
                session=sessao,
            )
            parcelas_atualizadas = result_upd.modified_count

        # Atualiza saldo_devedor_centavos (informativo) das parcelas ainda em aberto
        await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            },
            {"$set": {"saldo_devedor_centavos": novo_principal}},
            session=sessao,
        )

    # 5. Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="INCORPORAR_JUROS",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Incorporação de R$ {formatar_reais(valor_juros_centavos)} de juros ao capital. {formatar_reais(valor_atual)} -> {formatar_reais(novo_principal)}. Baixou {parcelas_baixadas} parcela(s). Recalcular: {payload.recalcular_juros}",
        dados_anteriores={"valor_principal_centavos": valor_atual},
        dados_novos={
            "valor_principal_centavos": novo_principal,
            "valor_incorporado_centavos": valor_juros_centavos,
            "parcelas_baixadas": parcelas_baixadas,
            "recalculou_juros": payload.recalcular_juros,
            "parcelas_atualizadas": parcelas_atualizadas,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return {
        "message": "Juros incorporados ao capital com sucesso",
        "valor_incorporado_centavos": valor_juros_centavos,
        "principal_anterior_centavos": valor_atual,
        "principal_atual_centavos": novo_principal,
        "parcelas_baixadas": parcelas_baixadas,
        "recalculou_juros": payload.recalcular_juros,
        "parcelas_atualizadas": parcelas_atualizadas,
    }


def _calcular_plano_prazo_fixo(emprestimo, parcelas, periodos):
    """
    Calcula (SEM persistir) o plano de re-amortização de um empréstimo de PRAZO
    FIXO. Mantém as parcelas já pagas e re-amortiza o SALDO DEVEDOR de capital ao
    longo de (parcelas em aberto + periodos) novas parcelas. Retorna um dict com
    as novas parcelas, totais e metadados. Levanta HTTPException nas validações.
    """

    periodicidade = emprestimo.get("periodicidade", "mensal")

    if not parcelas:
        raise HTTPException(status_code=400, detail="Empréstimo sem parcelas")

    pagas = [p for p in parcelas if p.get("status") == "pago"]
    abertas = [p for p in parcelas if p.get("status") != "pago"]
    if not abertas:
        raise HTTPException(
            status_code=400,
            detail="Todas as parcelas já foram pagas. Não há o que prorrogar."
        )

    capital_amortizado = sum(int(p.get("valor_principal_centavos", 0) or 0) for p in pagas)
    saldo_capital = int(emprestimo.get("valor_principal_centavos", 0) or 0) - capital_amortizado
    if saldo_capital <= 0:
        raise HTTPException(status_code=400, detail="Capital já totalmente amortizado.")

    taxa = emprestimo.get("taxa_juros_semanal") if periodicidade == "semanal" else emprestimo.get("taxa_juros_mensal")
    if not taxa:
        raise HTTPException(status_code=400, detail="Taxa de juros do empréstimo não encontrada.")

    n_abertas = len(abertas)
    novo_prazo_restante = n_abertas + periodos

    def _parse_dt(d):
        return datetime.fromisoformat(d) if isinstance(d, str) else d

    if pagas:
        data_base = max(_parse_dt(p["data_vencimento"]) for p in pagas)
    else:
        data_base = _parse_dt(emprestimo["data_inicio"])

    sim = SimulacaoRequest(
        valor_principal_centavos=saldo_capital,
        taxa_juros_mensal=emprestimo.get("taxa_juros_mensal"),
        prazo_meses=(novo_prazo_restante if periodicidade != "semanal" else None),
        metodo_calculo=emprestimo.get("metodo_calculo"),
        periodo_carencia_meses=0,
        taxa_multa_atraso=emprestimo.get("taxa_multa_atraso", 2.0),
        taxa_juros_mora_diario=emprestimo.get("taxa_juros_mora_diario", 0.033),
        periodicidade=periodicidade,
        taxa_juros_semanal=emprestimo.get("taxa_juros_semanal"),
        prazo_semanas=(novo_prazo_restante if periodicidade == "semanal" else None),
        dia_vencimento=emprestimo.get("dia_vencimento"),
    )
    novas_sim = gerar_parcelas_simulacao(sim, data_base, emprestimo.get("dia_vencimento"))

    numero_base = max((int(p.get("numero_parcela", 0) or 0) for p in pagas), default=0)
    total_final = numero_base + len(novas_sim)
    hoje = datetime.now(timezone.utc)

    novas = []
    for idx, p in enumerate(novas_sim):
        data_venc = datetime.fromisoformat(p.data_vencimento)
        novas.append({
            "numero_parcela": numero_base + idx + 1,
            "data_vencimento": p.data_vencimento,
            "valor_principal_centavos": p.valor_principal_centavos,
            "valor_juros_centavos": p.valor_juros_centavos,
            "valor_total_centavos": p.valor_total_centavos,
            "saldo_devedor_centavos": p.saldo_devedor_centavos,
            "status": "atrasado" if data_venc < hoje else "pendente",
        })

    valor_total_pagas = sum(int(p.get("valor_total_centavos", 0) or 0) for p in pagas)
    novo_valor_total = valor_total_pagas + sum(d["valor_total_centavos"] for d in novas)

    return {
        "tipo": "prazo_fixo",
        "periodicidade": periodicidade,
        "saldo_capital_centavos": saldo_capital,
        "abertas_ids": [p["id"] for p in abertas],
        "n_abertas": n_abertas,
        "pagas_count": len(pagas),
        "numero_base": numero_base,
        "total_final": total_final,
        "novas": novas,
        "novo_valor_total_centavos": novo_valor_total,
        "novo_valor_juros_centavos": novo_valor_total - int(emprestimo.get("valor_principal_centavos", 0) or 0),
        "valor_parcela_centavos": novas[0]["valor_total_centavos"] if novas else 0,
    }


async def _prorrogar_prazo_fixo(emprestimo, emprestimo_id, context_id, periodos, current_user, request):
    """Executa a prorrogação (re-amortização) de um empréstimo de prazo fixo."""

    periodicidade = emprestimo.get("periodicidade", "mensal")

    parcelas = await db.parcelas.find({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    }).sort("numero_parcela", 1).to_list(length=None)

    plano = _calcular_plano_prazo_fixo(emprestimo, parcelas, periodos)

    agora = datetime.now(timezone.utc).isoformat()
    # Soft-delete das parcelas em aberto (serão reprogramadas)
    await db.parcelas.update_many(
        {"id": {"$in": plano["abertas_ids"]}},
        {"$set": {
            "deleted": True,
            "deleted_at": agora,
            "deleted_motivo": f"Reprogramada por prorrogação (+{periodos} {periodicidade})",
            "updated_at": agora
        }}
    )

    novas_docs = []
    for d in plano["novas"]:
        novas_docs.append({
            "id": str(uuid.uuid4()),
            "emprestimo_id": emprestimo_id,
            "cliente_id": emprestimo.get("cliente_id"),
            "usuario_id": context_id,
            "numero_parcela": d["numero_parcela"],
            "data_vencimento": d["data_vencimento"],
            "valor_principal_centavos": d["valor_principal_centavos"],
            "valor_juros_centavos": d["valor_juros_centavos"],
            "valor_total_centavos": d["valor_total_centavos"],
            "valor_pago_centavos": 0,
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "dias_atraso": 0,
            "saldo_devedor_centavos": d["saldo_devedor_centavos"],
            "total_parcelas": plano["total_final"],
            "status": d["status"],
            "data_pagamento": None,
            "deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    if novas_docs:
        await db.parcelas.insert_many(novas_docs)

    await db.parcelas.update_many(
        {"emprestimo_id": emprestimo_id, "deleted": {"$ne": True}},
        {"$set": {"total_parcelas": plano["total_final"]}}
    )

    update_emprestimo = {
        "valor_total_com_juros_centavos": plano["novo_valor_total_centavos"],
        "valor_total_juros_centavos": plano["novo_valor_juros_centavos"],
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    if periodicidade == "semanal":
        update_emprestimo["prazo_semanas"] = plano["total_final"]
    else:
        update_emprestimo["prazo_meses"] = plano["total_final"]

    parcelas_antes = plano["numero_base"] + plano["n_abertas"]
    prorrogacao_entry = {
        "id": str(uuid.uuid4()),
        "data": datetime.now(timezone.utc).isoformat(),
        "periodos": periodos,
        "periodicidade": periodicidade,
        "metodo_calculo": emprestimo.get("metodo_calculo"),
        "tipo": "prazo_fixo",
        "parcelas_antes": parcelas_antes,
        "parcelas_depois": plano["total_final"],
        "saldo_reamortizado_centavos": plano["saldo_capital_centavos"],
        "novo_valor_total_centavos": plano["novo_valor_total_centavos"],
        "valor_parcela_centavos": plano["valor_parcela_centavos"],
        "usuario_email": current_user.email,
    }

    await db.emprestimos.update_one(
        {"id": emprestimo_id},
        {"$set": update_emprestimo, "$push": {"historico_prorrogacoes": prorrogacao_entry}}
    )

    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="PRORROGAR_EMPRESTIMO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=(f"Prorrogou empréstimo de prazo fixo ({emprestimo.get('metodo_calculo')}) "
                  f"por {periodos} {periodicidade}(s). Saldo re-amortizado em "
                  f"{len(novas_docs)} parcelas. Total: {plano['total_final']}"),
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    novas_parcelas_info = [
        {
            "numero_parcela": d["numero_parcela"],
            "data_vencimento": d["data_vencimento"],
            "valor_total_centavos": d["valor_total_centavos"],
            "tipo": "reprogramada"
        }
        for d in novas_docs
    ]

    return {
        "mensagem": (f"Empréstimo prorrogado por {periodos} {periodicidade}(s). "
                     f"Saldo de R$ {formatar_reais(plano['saldo_capital_centavos'])} re-amortizado em {len(novas_docs)} parcelas "
                     f"de aprox. R$ {formatar_reais(plano['valor_parcela_centavos'])}"),
        "emprestimo_id": emprestimo_id,
        "periodos_adicionados": periodos,
        "novo_total_parcelas": plano["total_final"],
        "prorrogacao_id": prorrogacao_entry["id"],
        "novas_parcelas_criadas": novas_parcelas_info
    }


@router.post("/{emprestimo_id}/prorrogar")
async def prorrogar_emprestimo(
    emprestimo_id: str,
    prorrogacao: dict,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Prorroga um empréstimo na modalidade 'apenas_juros' (capital no final)
    
    Funcionalidade:
    - A última parcela (que contém principal + juros) é transformada em parcela de apenas juros
    - São criadas N novas parcelas de apenas juros
    - Uma nova última parcela é criada com principal + juros
    
    Args:
        emprestimo_id: ID do empréstimo a prorrogar
        prorrogacao: {"periodos": int} - quantidade de meses/semanas para prorrogar
        
    Returns:
        Informações sobre a prorrogação realizada
    """
    
    # Validar request
    periodos = prorrogacao.get('periodos')
    if not periodos or periodos <= 0:
        raise HTTPException(status_code=422, detail="Períodos deve ser maior que zero")
    
    context_id = get_user_context(current_user)
    
    # Buscar empréstimo
    emprestimo = await db.emprestimos.find_one({
        "id": emprestimo_id,
        "usuario_id": context_id
    })
    
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    
    # Validações
    if emprestimo.get("status") not in ["ativo", "inadimplente"]:
        raise HTTPException(
            status_code=400, 
            detail="Apenas empréstimos ativos ou inadimplentes podem ser prorrogados"
        )
    
    if emprestimo.get("metodo_calculo") != "apenas_juros":
        # Empréstimos com prazo fixo: re-amortiza o saldo devedor em mais parcelas.
        return await _prorrogar_prazo_fixo(
            emprestimo, emprestimo_id, context_id, periodos, current_user, request
        )
    
    # Buscar todas as parcelas ativas ordenadas
    parcelas_cursor = db.parcelas.find({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id,
        "deleted": {"$ne": True}
    }).sort("numero_parcela", 1)
    parcelas = await parcelas_cursor.to_list(length=None)
    
    if not parcelas:
        raise HTTPException(status_code=400, detail="Empréstimo sem parcelas")
    
    # Encontrar última parcela (que tem o principal)
    ultima_parcela = parcelas[-1]
    
    # Verificar se última parcela já foi paga
    if ultima_parcela.get("status") == "pago":
        raise HTTPException(
            status_code=400,
            detail="Não é possível prorrogar: última parcela já foi paga"
        )
    
    # Verificar se última parcela tem principal
    if ultima_parcela.get("valor_principal_centavos", 0) == 0:
        raise HTTPException(
            status_code=400,
            detail="Última parcela não contém principal. Verifique o empréstimo."
        )
    
    # Obter dados do empréstimo
    valor_principal_centavos = emprestimo.get("valor_principal_centavos", 0)
    periodicidade = emprestimo.get("periodicidade", "mensal")
    
    # Determinar taxa de juros baseada na periodicidade
    if periodicidade == "semanal":
        taxa_juros = emprestimo.get("taxa_juros_semanal")
        if not taxa_juros:
            raise HTTPException(status_code=400, detail="Taxa de juros semanal não encontrada")
    else:
        taxa_juros = emprestimo.get("taxa_juros_mensal")
        if not taxa_juros:
            raise HTTPException(status_code=400, detail="Taxa de juros mensal não encontrada")
    
    # Calcular juros por período
    juros_periodo = arredondar_centavos(valor_principal_centavos * (taxa_juros / 100))
    
    # Passo 1: Transformar última parcela em parcela de apenas juros
    await db.parcelas.update_one(
        {"id": ultima_parcela["id"]},
        {"$set": {
            "valor_principal_centavos": 0,
            "valor_juros_centavos": juros_periodo,
            "valor_total_centavos": juros_periodo,
            "saldo_devedor_centavos": valor_principal_centavos,
            "updated_at": datetime.now(timezone.utc).isoformat()
        }}
    )
    
    # Passo 2: Obter total de parcelas atual
    total_parcelas_atual = ultima_parcela.get("numero_parcela", len(parcelas))
    numero_proxima_parcela = total_parcelas_atual + 1
    
    # Passo 3: Criar novas parcelas de apenas juros
    novas_parcelas = []
    data_ultima_parcela = ultima_parcela.get("data_vencimento")
    if isinstance(data_ultima_parcela, str):
        data_ultima_parcela = datetime.fromisoformat(data_ultima_parcela)
    
    for i in range(periodos):
        # Calcular data de vencimento
        data_vencimento = calcular_data_vencimento(
            data_ultima_parcela,
            i + 1,
            dia_vencimento=None,
            periodicidade=periodicidade
        )
        
        parcela = {
            "id": str(uuid.uuid4()),
            "emprestimo_id": emprestimo_id,
            "cliente_id": emprestimo.get("cliente_id"),
            "usuario_id": context_id,
            "numero_parcela": numero_proxima_parcela + i,
            "data_vencimento": data_vencimento.isoformat(),
            "valor_principal_centavos": 0,
            "valor_juros_centavos": juros_periodo,
            "valor_total_centavos": juros_periodo,
            "valor_pago_centavos": 0,
            "valor_multa_centavos": 0,
            "valor_juros_mora_centavos": 0,
            "dias_atraso": 0,
            "saldo_devedor_centavos": valor_principal_centavos,
            "total_parcelas": None,  # Será atualizado depois
            "status": "pendente",
            "data_pagamento": None,
            "ativo": True,
            "deleted": False,
            "created_at": datetime.now(timezone.utc).isoformat()
        }
        novas_parcelas.append(parcela)
    
    # Passo 4: Criar nova última parcela (principal + juros)
    numero_ultima_nova = numero_proxima_parcela + periodos
    data_vencimento_final = calcular_data_vencimento(
        data_ultima_parcela,
        periodos + 1,
        dia_vencimento=None,
        periodicidade=periodicidade
    )
    
    parcela_final = {
        "id": str(uuid.uuid4()),
        "emprestimo_id": emprestimo_id,
        "cliente_id": emprestimo.get("cliente_id"),
        "usuario_id": context_id,
        "numero_parcela": numero_ultima_nova,
        "data_vencimento": data_vencimento_final.isoformat(),
        "valor_principal_centavos": valor_principal_centavos,
        "valor_juros_centavos": juros_periodo,
        "valor_total_centavos": valor_principal_centavos + juros_periodo,
        "valor_pago_centavos": 0,
        "valor_multa_centavos": 0,
        "valor_juros_mora_centavos": 0,
        "dias_atraso": 0,
        "saldo_devedor_centavos": 0,
        "total_parcelas": numero_ultima_nova,
        "status": "pendente",
        "data_pagamento": None,
        "ativo": True,
        "deleted": False,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    novas_parcelas.append(parcela_final)
    
    # Inserir novas parcelas no banco
    if novas_parcelas:
        await db.parcelas.insert_many(novas_parcelas)
    
    # Passo 5: Atualizar total_parcelas em todas as parcelas
    await db.parcelas.update_many(
        {"emprestimo_id": emprestimo_id},
        {"$set": {"total_parcelas": numero_ultima_nova}}
    )
    
    # Passo 6: Atualizar empréstimo
    update_emprestimo = {
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    
    # Atualizar prazo_meses ou prazo_semanas
    if periodicidade == "semanal":
        prazo_atual = emprestimo.get("prazo_semanas", 0)
        update_emprestimo["prazo_semanas"] = prazo_atual + periodos + 1
    else:
        prazo_atual = emprestimo.get("prazo_meses", 0)
        update_emprestimo["prazo_meses"] = prazo_atual + periodos + 1
    
    prorrogacao_entry = {
        "id": str(_uuid_hist.uuid4()),
        "data": datetime.now(timezone.utc).isoformat(),
        "periodos": periodos,
        "periodicidade": periodicidade,
        "metodo_calculo": "apenas_juros",
        "tipo": "apenas_juros",
        "parcelas_antes": total_parcelas_atual,
        "parcelas_depois": numero_ultima_nova,
        "saldo_reamortizado_centavos": int(valor_principal_centavos or 0),
        "juros_periodo_centavos": juros_periodo,
        "usuario_email": current_user.email,
    }

    await db.emprestimos.update_one(
        {"id": emprestimo_id},
        {"$set": update_emprestimo, "$push": {"historico_prorrogacoes": prorrogacao_entry}}
    )
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="PRORROGAR_EMPRESTIMO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Prorrogou empréstimo por {periodos} {periodicidade}(s). Total parcelas: {numero_ultima_nova}",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    # Preparar response
    novas_parcelas_info = [
        {
            "numero_parcela": p["numero_parcela"],
            "data_vencimento": p["data_vencimento"],
            "valor_total_centavos": p["valor_total_centavos"],
            "tipo": "apenas_juros" if p["valor_principal_centavos"] == 0 else "principal_juros"
        }
        for p in novas_parcelas
    ]
    
    return {
        "mensagem": f"Empréstimo prorrogado com sucesso por {periodos} {periodicidade}(s)",
        "emprestimo_id": emprestimo_id,
        "periodos_adicionados": periodos,
        "novo_total_parcelas": numero_ultima_nova,
        "prorrogacao_id": prorrogacao_entry["id"],
        "novas_parcelas_criadas": novas_parcelas_info
    }


@router.post("/{emprestimo_id}/prorrogar/preview")
async def prorrogar_preview(
    emprestimo_id: str,
    prorrogacao: dict,
    current_user: Usuario = Depends(get_current_user)
):
    """
    Prévia (sem persistir) da prorrogação: retorna o novo cronograma de parcelas
    e os totais para o usuário conferir antes de confirmar.
    """
    periodos = prorrogacao.get('periodos')
    if not periodos or periodos <= 0:
        raise HTTPException(status_code=422, detail="Períodos deve ser maior que zero")

    context_id = get_user_context(current_user)
    emprestimo = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id})
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")
    if emprestimo.get("status") not in ["ativo", "inadimplente"]:
        raise HTTPException(status_code=400, detail="Apenas empréstimos ativos ou inadimplentes podem ser prorrogados")

    periodicidade = emprestimo.get("periodicidade", "mensal")
    parcelas = await db.parcelas.find({
        "emprestimo_id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}
    }).sort("numero_parcela", 1).to_list(length=None)

    metodo = emprestimo.get("metodo_calculo")

    if metodo != "apenas_juros":
        plano = _calcular_plano_prazo_fixo(emprestimo, parcelas, periodos)
        return {
            "tipo": "prazo_fixo",
            "metodo_calculo": metodo,
            "periodicidade": periodicidade,
            "periodos_adicionados": periodos,
            "novo_total_parcelas": plano["total_final"],
            "novo_valor_total_com_juros_centavos": plano["novo_valor_total_centavos"],
            "novo_valor_total_juros_centavos": plano["novo_valor_juros_centavos"],
            "valor_parcela_centavos": plano["valor_parcela_centavos"],
            "saldo_reamortizado_centavos": plano["saldo_capital_centavos"],
            "parcelas_preview": [
                {
                    "numero_parcela": d["numero_parcela"],
                    "data_vencimento": d["data_vencimento"],
                    "valor_principal_centavos": d["valor_principal_centavos"],
                    "valor_juros_centavos": d["valor_juros_centavos"],
                    "valor_total_centavos": d["valor_total_centavos"],
                }
                for d in plano["novas"]
            ],
        }

    # Prévia para 'apenas_juros'
    if not parcelas:
        raise HTTPException(status_code=400, detail="Empréstimo sem parcelas")
    ultima = parcelas[-1]
    if ultima.get("status") == "pago":
        raise HTTPException(status_code=400, detail="Não é possível prorrogar: última parcela já foi paga")
    if ultima.get("valor_principal_centavos", 0) == 0:
        raise HTTPException(status_code=400, detail="Última parcela não contém principal.")

    valor_principal_centavos = int(emprestimo.get("valor_principal_centavos", 0) or 0)
    taxa = emprestimo.get("taxa_juros_semanal") if periodicidade == "semanal" else emprestimo.get("taxa_juros_mensal")
    if not taxa:
        raise HTTPException(status_code=400, detail="Taxa de juros do empréstimo não encontrada.")
    juros_periodo = arredondar_centavos(valor_principal_centavos * (taxa / 100))

    data_ultima = ultima.get("data_vencimento")
    if isinstance(data_ultima, str):
        data_ultima = datetime.fromisoformat(data_ultima)
    total_atual = int(ultima.get("numero_parcela", len(parcelas)))

    preview = [{
        "numero_parcela": total_atual,
        "data_vencimento": ultima.get("data_vencimento"),
        "valor_principal_centavos": 0,
        "valor_juros_centavos": juros_periodo,
        "valor_total_centavos": juros_periodo,
    }]
    for i in range(periodos):
        dv = calcular_data_vencimento(data_ultima, i + 1, None, periodicidade)
        preview.append({
            "numero_parcela": total_atual + 1 + i,
            "data_vencimento": dv.isoformat(),
            "valor_principal_centavos": 0,
            "valor_juros_centavos": juros_periodo,
            "valor_total_centavos": juros_periodo,
        })
    dv_final = calcular_data_vencimento(data_ultima, periodos + 1, None, periodicidade)
    preview.append({
        "numero_parcela": total_atual + periodos + 1,
        "data_vencimento": dv_final.isoformat(),
        "valor_principal_centavos": valor_principal_centavos,
        "valor_juros_centavos": juros_periodo,
        "valor_total_centavos": valor_principal_centavos + juros_periodo,
    })

    return {
        "tipo": "apenas_juros",
        "metodo_calculo": metodo,
        "periodicidade": periodicidade,
        "periodos_adicionados": periodos,
        "novo_total_parcelas": total_atual + periodos + 1,
        "novo_valor_total_com_juros_centavos": None,
        "novo_valor_total_juros_centavos": None,
        "valor_parcela_centavos": juros_periodo,
        "saldo_reamortizado_centavos": valor_principal_centavos,
        "parcelas_preview": preview,
    }


def _build_recibo_prorrogacao_pdf(emprestimo_id, emprestimo, prorrogacao, cliente, parcelas_ativas, credor_nome):
    """Monta o PDF do comprovante de prorrogação (novo cronograma) e retorna io.BytesIO."""

    def _parse_dt(v):
        try:
            return datetime.fromisoformat(str(v).replace("Z", "+00:00"))
        except (ValueError, TypeError, AttributeError):
            return None

    def fmt_moeda(centavos):
        return f"R$ {formatar_reais(centavos)}"

    def fmt_data(dt):
        if isinstance(dt, str):
            dt = _parse_dt(dt)
        return dt.strftime("%d/%m/%Y") if dt else "-"

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer, pagesize=A4,
        topMargin=1.5 * cm, bottomMargin=1.2 * cm, leftMargin=2 * cm, rightMargin=2 * cm
    )
    elements = []
    styles = getSampleStyleSheet()

    PRIMARY = colors.HexColor('#10b981')
    DARK = colors.HexColor('#1f2937')
    GRAY = colors.HexColor('#6b7280')
    LIGHT = colors.HexColor('#f3f4f6')

    header_style = ParagraphStyle('H', parent=styles['Heading1'], fontSize=22,
                                  textColor=PRIMARY, alignment=TA_CENTER, spaceAfter=2,
                                  fontName='Helvetica-Bold')
    sub_style = ParagraphStyle('S', parent=styles['Normal'], fontSize=10, textColor=GRAY,
                               alignment=TA_CENTER, spaceAfter=12)
    section = ParagraphStyle('Sec', parent=styles['Heading2'], fontSize=11, textColor=DARK,
                             spaceBefore=8, spaceAfter=4, fontName='Helvetica-Bold',
                             backColor=LIGHT, borderPadding=(6, 6, 6, 6), leftIndent=6)
    decl = ParagraphStyle('Decl', parent=styles['Normal'], fontSize=11, textColor=DARK,
                          alignment=TA_LEFT, leading=18, spaceBefore=8)

    elements.append(Paragraph("COMPROVANTE DE PRORROGAÇÃO", header_style))
    elements.append(Paragraph("Kredor - Sistema de Gestão de Empréstimos", sub_style))

    line = Table([['', '']], colWidths=[17 * cm])
    line.setStyle(TableStyle([
        ('LINEABOVE', (0, 0), (-1, 0), 2, PRIMARY),
        ('TOPPADDING', (0, 0), (-1, -1), 0), ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
    ]))
    elements.append(line)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Dados do Cliente", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_cliente = [
        ['Nome:', cliente.get('nome', 'N/A')],
        ['CPF/CNPJ:', cliente.get('cpf_cnpj') or cliente.get('cpf') or 'N/A'],
        ['Telefone:', cliente.get('telefone', 'N/A')],
    ]
    tc = Table(dados_cliente, colWidths=[4 * cm, 13 * cm])
    tc.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 2),
    ]))
    elements.append(tc)
    elements.append(Spacer(1, 0.3 * cm))

    periodicidade = prorrogacao.get("periodicidade", "mensal")
    unidade = "semana(s)" if periodicidade == "semanal" else "mês(es)"
    elements.append(Paragraph("Dados da Prorrogação", section))
    elements.append(Spacer(1, 0.2 * cm))
    dados_pr = [
        ['Contrato:', f"#{emprestimo_id[:8].upper()}"],
        ['Data da Prorrogação:', fmt_data(prorrogacao.get("data"))],
        ['Períodos adicionados:', f"{prorrogacao.get('periodos')} {unidade}"],
        ['Parcelas (antes / depois):', f"{prorrogacao.get('parcelas_antes')} / {prorrogacao.get('parcelas_depois')}"],
        ['Saldo re-amortizado:', fmt_moeda(prorrogacao.get("saldo_reamortizado_centavos"))],
    ]
    tp = Table(dados_pr, colWidths=[6 * cm, 11 * cm])
    tp.setStyle(TableStyle([
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
        ('TEXTCOLOR', (0, 0), (0, -1), GRAY), ('TEXTCOLOR', (1, 0), (1, -1), DARK),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6), ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('LINEBELOW', (0, 0), (-1, -2), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(tp)
    elements.append(Spacer(1, 0.4 * cm))

    elements.append(Paragraph("Novo Cronograma de Parcelas", section))
    elements.append(Spacer(1, 0.2 * cm))
    status_label = {"pago": "Paga", "pendente": "Pendente", "atrasado": "Atrasada", "parcial": "Parcial"}
    linhas = [['#', 'Vencimento', 'Valor', 'Situação']]
    for p in parcelas_ativas:
        linhas.append([
            str(p.get("numero_parcela", "")),
            fmt_data(p.get("data_vencimento")),
            fmt_moeda(p.get("valor_total_centavos")),
            status_label.get(p.get("status"), p.get("status", "-")),
        ])
    tabela = Table(linhas, colWidths=[2 * cm, 5 * cm, 5 * cm, 5 * cm])
    tabela.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), PRIMARY),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 9),
        ('ALIGN', (0, 0), (0, -1), 'CENTER'),
        ('ALIGN', (2, 0), (2, -1), 'RIGHT'),
        ('ALIGN', (3, 0), (3, -1), 'CENTER'),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, LIGHT]),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5), ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e5e7eb')),
    ]))
    elements.append(tabela)
    elements.append(Spacer(1, 0.5 * cm))

    total_ativo = sum(int(p.get("valor_total_centavos", 0) or 0) for p in parcelas_ativas)
    texto = (
        f"O empréstimo de contrato <b>#{emprestimo_id[:8].upper()}</b> foi prorrogado em "
        f"<b>{prorrogacao.get('periodos')} {unidade}</b>. O novo cronograma acima passa a valer, "
        f"totalizando <b>{fmt_moeda(total_ativo)}</b> em parcelas."
    )
    elements.append(Paragraph(texto, decl))
    elements.append(Spacer(1, 1.2 * cm))

    assinatura = Table([['_' * 40], [f"{credor_nome or 'Credor'}"]], colWidths=[10 * cm])
    assinatura.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTSIZE', (0, 1), (0, 1), 9), ('TEXTCOLOR', (0, 1), (0, 1), GRAY),
        ('TOPPADDING', (0, 1), (0, 1), 2),
    ]))
    elements.append(assinatura)
    elements.append(Spacer(1, 0.6 * cm))

    footer = ParagraphStyle('F', parent=styles['Normal'], fontSize=7, textColor=GRAY, alignment=TA_CENTER)
    elements.append(Paragraph(
        f"Documento gerado em {datetime.now().strftime('%d/%m/%Y às %H:%M')} - Kredor", footer))

    doc.build(elements)
    buffer.seek(0)
    return buffer


async def _obter_dados_recibo_prorrogacao(emprestimo_id, prorrogacao_id, context_id):
    """Busca empréstimo, a prorrogação no histórico, cliente e parcelas ativas."""
    emprestimo = await db.emprestimos.find_one({"id": emprestimo_id, "usuario_id": context_id}, {"_id": 0})
    if not emprestimo:
        raise HTTPException(status_code=404, detail="Empréstimo não encontrado")

    historico = emprestimo.get("historico_prorrogacoes") or []
    prorrogacao = next((h for h in historico if h.get("id") == prorrogacao_id), None)
    if not prorrogacao:
        raise HTTPException(status_code=404, detail="Prorrogação não encontrada")

    cliente = await db.clientes.find_one({"id": emprestimo.get("cliente_id")}, {"_id": 0}) or {}
    parcelas_ativas = await db.parcelas.find({
        "emprestimo_id": emprestimo_id, "usuario_id": context_id, "deleted": {"$ne": True}
    }).sort("numero_parcela", 1).to_list(length=None)
    return emprestimo, prorrogacao, cliente, parcelas_ativas


@router.get("/{emprestimo_id}/recibo-prorrogacao/{prorrogacao_id}")
async def recibo_prorrogacao_pdf(
    emprestimo_id: str,
    prorrogacao_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera o Comprovante de Prorrogação (PDF) com o novo cronograma."""
    context_id = get_user_context(current_user)
    emprestimo, prorrogacao, cliente, parcelas_ativas = await _obter_dados_recibo_prorrogacao(
        emprestimo_id, prorrogacao_id, context_id
    )
    credor_nome = getattr(current_user, 'nome', None)
    buffer = _build_recibo_prorrogacao_pdf(emprestimo_id, emprestimo, prorrogacao, cliente, parcelas_ativas, credor_nome)
    nome_safe = (cliente.get('nome', 'cliente') or 'cliente').replace(' ', '_')[:30]
    filename = f"comprovante_prorrogacao_{nome_safe}_{emprestimo_id[:8]}.pdf"
    return StreamingResponse(
        buffer, media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.post("/{emprestimo_id}/recibo-prorrogacao/{prorrogacao_id}/whatsapp")
async def enviar_recibo_prorrogacao_whatsapp(
    emprestimo_id: str,
    prorrogacao_id: str,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Envia o comprovante de prorrogação (PDF) ao cliente via WhatsApp."""

    context_id = get_user_context(current_user)
    emprestimo, prorrogacao, cliente, parcelas_ativas = await _obter_dados_recibo_prorrogacao(
        emprestimo_id, prorrogacao_id, context_id
    )
    telefone = cliente.get("telefone") or cliente.get("celular")
    if not telefone:
        raise HTTPException(status_code=400, detail="Cliente não possui telefone cadastrado")

    credor_nome = getattr(current_user, 'nome', None)
    buffer = _build_recibo_prorrogacao_pdf(emprestimo_id, emprestimo, prorrogacao, cliente, parcelas_ativas, credor_nome)
    b64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

    periodicidade = prorrogacao.get("periodicidade", "mensal")
    unidade = "semana(s)" if periodicidade == "semanal" else "mês(es)"
    legenda = (
        f"Olá {cliente.get('nome', '')}! Seu empréstimo foi prorrogado em "
        f"{prorrogacao.get('periodos')} {unidade}. Segue o novo cronograma de parcelas. Obrigado!"
    )
    nome_safe = (cliente.get('nome', 'cliente') or 'cliente').replace(' ', '_')[:30]
    filename = f"comprovante_prorrogacao_{nome_safe}.pdf"

    resultado = await enviar_documento_whatsapp(
        usuario_id=context_id,
        numero_destino=telefone,
        base64_documento=b64,
        nome_arquivo=filename,
        legenda=legenda,
    )

    if not resultado.get("success"):
        err = resultado.get("error")
        msg = resultado.get("message", "Falha ao enviar pelo WhatsApp")
        if err == "whatsapp_nao_conectado":
            msg = "WhatsApp não está conectado. Conecte sua conta em Configurações › WhatsApp."
        elif err == "evolution_nao_configurada":
            msg = "Integração de WhatsApp não configurada. Configure a Evolution API primeiro."
        raise HTTPException(status_code=400, detail=msg)

    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="ENVIAR_RECIBO_WHATSAPP",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Enviou comprovante de prorrogação via WhatsApp para {cliente.get('nome', 'cliente')}",
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )

    return {"success": True, "message": "Comprovante enviado pelo WhatsApp", "numero": resultado.get("numero_enviado")}

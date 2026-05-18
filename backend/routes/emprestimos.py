"""
Rotas de Empréstimos
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from fastapi.responses import StreamingResponse
from typing import List, Optional
from datetime import datetime, timezone
import io

from config import db
from models.emprestimo import (
    Emprestimo, EmprestimoCreate, EmprestimoUpdate, Parcela,
    SimulacaoRequest, SimulacaoResponse, ProrrogacaoRequest, ProrrogacaoResponse,
    AmortizacaoRequest
)
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.calculos import gerar_parcelas_simulacao
from services.auditoria import registrar_auditoria
from services.permissao_service import verificar_pode_criar_emprestimo, verificar_plano_ativo

router = APIRouter()


@router.post("/simular", response_model=SimulacaoResponse)
async def simular_emprestimo(
    simulacao: SimulacaoRequest,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """Simula um empréstimo"""
    
    # Validar campos obrigatórios baseado na periodicidade
    if simulacao.periodicidade == "semanal":
        if not simulacao.taxa_juros_semanal or not simulacao.prazo_semanas:
            raise HTTPException(
                status_code=422, 
                detail="Para simulação semanal, taxa_juros_semanal e prazo_semanas são obrigatórios"
            )
    else:  # mensal
        if not simulacao.taxa_juros_mensal or not simulacao.prazo_meses:
            raise HTTPException(
                status_code=422, 
                detail="Para simulação mensal, taxa_juros_mensal e prazo_meses são obrigatórios"
            )
    
    data_inicio = datetime.now(timezone.utc)
    parcelas = gerar_parcelas_simulacao(simulacao, data_inicio, simulacao.dia_vencimento)
    
    valor_total = sum(p.valor_total for p in parcelas)
    valor_juros = valor_total - simulacao.valor_principal
    
    return SimulacaoResponse(
        valor_principal=simulacao.valor_principal,
        taxa_juros_mensal=simulacao.taxa_juros_mensal,
        prazo_meses=simulacao.prazo_meses,
        metodo_calculo=simulacao.metodo_calculo,
        periodo_carencia_meses=simulacao.periodo_carencia_meses,
        periodicidade=simulacao.periodicidade,
        taxa_juros_semanal=simulacao.taxa_juros_semanal,
        prazo_semanas=simulacao.prazo_semanas,
        valor_total_com_juros=round(valor_total, 2),
        valor_total_juros=round(valor_juros, 2),
        parcelas=parcelas
    )


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
        
        juros_periodo = emprestimo.valor_principal * (taxa_juros / 100)
        
        # Criar empréstimo
        emprestimo_data = emprestimo.model_dump()
        emprestimo_data["data_inicio"] = data_inicio
        emprestimo_data["valor_total_com_juros"] = 0.0  # Será calculado ao quitar
        emprestimo_data["valor_total_juros"] = 0.0  # Será calculado ao quitar
        
        emprestimo_obj = Emprestimo(**emprestimo_data)
        doc = emprestimo_obj.model_dump()
        doc["data_inicio"] = doc["data_inicio"].isoformat()
        doc["created_at"] = doc["created_at"].isoformat()
        doc["usuario_id"] = context_id
        doc["created_by"] = current_user.email
        
        await db.emprestimos.insert_one(doc)
        
        # Gerar TODAS as parcelas desde data_inicio até ter 1 parcela futura
        from services.calculos import calcular_data_vencimento
        numero_parcela = 1
        parcelas_criadas = 0
        
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
                valor_principal=0.0,
                valor_juros=round(juros_periodo, 2),
                valor_total=round(juros_periodo, 2),
                saldo_devedor=emprestimo.valor_principal,
                total_parcelas=None
            )
            
            parcela_doc = parcela.model_dump()
            parcela_doc["status"] = status_parcela
            parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
            parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
            parcela_doc["usuario_id"] = context_id
            
            await db.parcelas.insert_one(parcela_doc)
            parcelas_criadas += 1
            
            # Se esta parcela é futura, paramos (sempre ter 1 pendente)
            if data_vencimento >= hoje:
                break
            
            numero_parcela += 1
        
        # Registrar auditoria
        await registrar_auditoria(
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            acao="CRIAR_EMPRESTIMO_ABERTO",
            entidade="emprestimos",
            entidade_id=emprestimo_obj.id,
            detalhes=f"Criou empréstimo aberto {periodicidade_label}: R$ {emprestimo.valor_principal:,.2f} - {emprestimo.metodo_calculo} ({parcelas_criadas} parcelas geradas)",
            dados_novos={
                "valor_principal": emprestimo.valor_principal, 
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
        valor_principal=emprestimo.valor_principal,
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
    
    valor_total = sum(p.valor_total for p in parcelas_sim)
    valor_juros = valor_total - emprestimo.valor_principal
    
    # Criar empréstimo
    emprestimo_data = emprestimo.model_dump()
    emprestimo_data["data_inicio"] = data_inicio
    emprestimo_data["valor_total_com_juros"] = round(valor_total, 2)
    emprestimo_data["valor_total_juros"] = round(valor_juros, 2)
    
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
            valor_principal=p.valor_principal,
            valor_juros=p.valor_juros,
            valor_total=p.valor_total,
            saldo_devedor=p.saldo_devedor
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
        detalhes=f"Criou empréstimo: R$ {emprestimo.valor_principal:,.2f} - {emprestimo.metodo_calculo}",
        dados_novos={
            "valor": emprestimo.valor_principal,
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
    from services.pagination_service import paginated_find
    from services.soft_delete_service import SoftDeleteService
    from services.auth_utils import is_owner
    
    context_id = get_user_context(current_user)
    
    # Se pedir lixeira, verifique permissão
    if lixeira:
        if current_user.perfil not in ['admin', 'superadmin'] and not is_owner(current_user):
             raise HTTPException(status_code=403, detail="Apenas administradores podem acessar a lixeira")
             
        # Usar serviço de soft delete para listar
        result = await SoftDeleteService.list_deleted(
            "emprestimos",
            context_id,
            skip=(page - 1) * limit,
            limit=limit
        )
        
        # Enriquecer com nome do cliente e formatar datas
        for item in result["items"]:
             # Buscar nome do cliente
             cliente = await db.clientes.find_one({"id": item.get("cliente_id")}, {"nome": 1})
             item["cliente_nome"] = cliente["nome"] if cliente else "Cliente Removido"
             
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
    
    # Converter datas e calcular total de juros acumulado para empréstimos abertos
    for e in result["items"]:
        if "data_inicio" in e and isinstance(e["data_inicio"], str):
            e["data_inicio"] = datetime.fromisoformat(e["data_inicio"])
        if "created_at" in e and isinstance(e["created_at"], str):
            e["created_at"] = datetime.fromisoformat(e["created_at"])
        
        # Para empréstimos abertos, calcular total de juros das parcelas já geradas
        if e.get("sem_prazo"):
            parcelas = await db.parcelas.find(
                {
                    "emprestimo_id": e["id"],
                    "usuario_id": e.get("usuario_id"),
                    "deleted": {"$ne": True},
                },
                {"_id": 0, "valor_juros": 1}
            ).to_list(1000)
            
            total_juros_gerado = sum(p.get("valor_juros", 0) for p in parcelas)
            e["valor_total_juros"] = total_juros_gerado
            e["valor_total_com_juros"] = e["valor_principal"] + total_juros_gerado
    
    return result


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
    if parcelas_pendentes == 0 and emprestimo.get("status") != "quitado":
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
                
                valor_devido = p["valor_total"] - p["valor_pago"]
                p["valor_multa"] = round(valor_devido * (taxa_multa / 100), 2)
                p["valor_juros_mora"] = round(valor_devido * (taxa_mora_diario / 100) * dias_atraso, 2)
                
                await db.parcelas.update_one(
                    {"id": p["id"], "usuario_id": context_id, "deleted": {"$ne": True}},
                    {"$set": {
                        "dias_atraso": dias_atraso,
                        "status": "atrasado",
                        "valor_multa": p["valor_multa"],
                        "valor_juros_mora": p["valor_juros_mora"]
                    }}
                )
    
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
        "valor_principal", "taxa_juros_mensal", "taxa_juros_semanal",
        "prazo_meses", "prazo_semanas",
        "metodo_calculo", "periodo_carencia_meses", "data_inicio"
    ]
    
    alterou_financeiro = any(
        getattr(update_data, campo) is not None and getattr(update_data, campo) != emprestimo_original.get(campo)
        for campo in campos_financeiros
    )
    
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
            "valor_principal": updated_dict.get("valor_principal", emprestimo_original["valor_principal"]),
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
        
        valor_total = sum(p.valor_total for p in parcelas_sim)
        valor_juros = valor_total - sim_req.valor_principal
        
        updated_dict["valor_total_com_juros"] = round(valor_total, 2)
        updated_dict["valor_total_juros"] = round(valor_juros, 2)
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
                valor_principal=p.valor_principal,
                valor_juros=p.valor_juros,
                valor_total=p.valor_total,
                saldo_devedor=p.saldo_devedor
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
    from services.soft_delete_service import soft_delete_emprestimo, SoftDeleteService
    from services.logging_service import get_logger
    
    logger = get_logger("jurofacil.emprestimos")
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
        # Fix #12: Hard delete exige perfil admin ou superadmin
        if current_user.perfil not in ['admin', 'superadmin']:
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
            "valor_principal": emprestimo.get("valor_principal")
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
    from services.soft_delete_service import restore_emprestimo
    from services.logging_service import get_logger
    from services.auth_utils import is_owner
    
    # Verificar permissão
    if current_user.perfil not in ['admin', 'superadmin'] and not is_owner(current_user):
         raise HTTPException(status_code=403, detail="Apenas administradores podem restaurar itens")
    
    logger = get_logger("jurofacil.emprestimos")
    
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
    from utils.relatorio_templates import gerar_pdf_profissional
    from utils.excel_templates import gerar_excel_profissional
    
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
    total_pago = sum(p.get("valor_pago", 0) for p in parcelas if p.get("status") == "pago")
    total_restante = emprestimo["valor_total_com_juros"] - total_pago
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
            except:
                return data_str[:10] if len(data_str) > 10 else data_str
        else:
            return data_str.strftime("%d/%m/%Y")
    
    def formatar_moeda(valor):
        return f"R$ {valor:,.2f}"
    
    # Preparar dados do resumo executivo
    dados_resumo = [
        {"titulo": "Valor Principal", "valor": formatar_moeda(emprestimo["valor_principal"]), "cor": "primaria"},
        {"titulo": "Total com Juros", "valor": formatar_moeda(emprestimo["valor_total_com_juros"]), "cor": "secundaria"},
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
            "Valor": formatar_moeda(p.get("valor_total", 0)),
            "Valor Pago": formatar_moeda(p.get("valor_pago", 0)),
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
    
    # Buscar última parcela gerada
    ultima_parcela = await db.parcelas.find_one(
        {"emprestimo_id": emprestimo_id},
        {"_id": 0},
        sort=[("numero_parcela", -1)]
    )
    
    if not ultima_parcela:
        raise HTTPException(status_code=400, detail="Nenhuma parcela encontrada")
    
    # Calcular juros do período atual (mensal ou semanal)
    periodicidade = emprestimo.get("periodicidade", "mensal")
    if periodicidade == "semanal":
        taxa_juros = emprestimo.get("taxa_juros_semanal", 0)
    else:
        taxa_juros = emprestimo.get("taxa_juros_mensal", 0)
    
    juros_periodo = emprestimo["valor_principal"] * (taxa_juros / 100)
    
    # Gerar parcela final (capital + juros)
    from services.calculos import calcular_data_vencimento
    
    data_inicio_emp = datetime.fromisoformat(emprestimo["data_inicio"])
    numero_proxima = ultima_parcela["numero_parcela"] + 1
    
    data_vencimento_final = calcular_data_vencimento(
        data_inicio_emp,
        numero_proxima,
        emprestimo.get("dia_vencimento"),
        periodicidade
    )
    
    parcela_final = Parcela(
        emprestimo_id=emprestimo_id,
        numero_parcela=numero_proxima,
        data_vencimento=data_vencimento_final,
        valor_principal=emprestimo["valor_principal"],  # Capital total
        valor_juros=round(juros_periodo, 2),
        valor_total=round(emprestimo["valor_principal"] + juros_periodo, 2),
        saldo_devedor=0.0,  # Quitado
        total_parcelas=numero_proxima
    )
    
    parcela_doc = parcela_final.model_dump()
    parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
    parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
    parcela_doc["usuario_id"] = context_id
    
    await db.parcelas.insert_one(parcela_doc)
    
    # Atualizar total_parcelas de todas as parcelas
    await db.parcelas.update_many(
        {"emprestimo_id": emprestimo_id},
        {"$set": {"total_parcelas": numero_proxima}}
    )
    
    # Calcular totais
    todas_parcelas = await db.parcelas.find(
        {
            "emprestimo_id": emprestimo_id,
            "usuario_id": current_user.id,
            "deleted": {"$ne": True},
        },
        {"_id": 0}
    ).to_list(1000)
    
    valor_total_com_juros = sum(p["valor_total"] for p in todas_parcelas)
    valor_total_juros = valor_total_com_juros - emprestimo["valor_principal"]
    
    # Atualizar empréstimo — marcar como quitado
    await db.emprestimos.update_one(
        {"id": emprestimo_id},
        {"$set": {
            "status": "quitado",
            "valor_total_com_juros": round(valor_total_com_juros, 2),
            "valor_total_juros": round(valor_total_juros, 2),
            "prazo_meses": numero_proxima
        }}
    )
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="QUITAR_EMPRESTIMO_ABERTO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Quitação empréstimo aberto: parcela final #{numero_proxima}, total R$ {valor_total_com_juros:.2f}",
        dados_novos={
            "parcela_final": numero_proxima,
            "valor_total": round(valor_total_com_juros, 2)
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "message": "Parcela final gerada com sucesso",
        "parcela_numero": numero_proxima,
        "valor_total": round(emprestimo["valor_principal"] + juros_periodo, 2),
        "total_parcelas": numero_proxima,
        "valor_total_emprestimo": round(valor_total_com_juros, 2)
    }



@router.get("/{emprestimo_id}/compartilhar-pdf")
async def compartilhar_emprestimo_pdf(
    emprestimo_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera PDF com detalhes do empréstimo para compartilhar com cliente"""
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib.enums import TA_CENTER, TA_RIGHT, TA_LEFT
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    
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
    from services.logging_service import get_logger
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
    PRIMARY_COLOR = colors.HexColor('#10b981')  # Verde GestorCred
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
    elements.append(Paragraph("GestorCred", header_style))
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
    valor_principal = emprestimo.get('valor_principal') or emprestimo.get('valor_emprestimo', 0)
    
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
        ['Valor Emprestado:', f"R$ {valor_principal:,.2f}"],
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
                f"R$ {p.get('valor_total', 0):,.2f}",
                f"R$ {p.get('valor_pago', 0):,.2f}",
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
    total_a_pagar = sum(p.get('valor_total', 0) for p in parcelas)  # Soma de todas as parcelas
    total_pago = sum(p.get('valor_pago', 0) for p in parcelas)  # Total já pago
    total_devido = total_a_pagar - total_pago  # Saldo pendente
    total_juros = total_a_pagar - valor_principal  # Total de juros
    
    # Box com resumo financeiro destacado
    dados_totais = [
        ['Total Emprestado:', f"R$ {valor_principal:,.2f}"],
        ['Total de Juros:', f"R$ {total_juros:,.2f}"],
        ['Total a Pagar:', f"R$ {total_a_pagar:,.2f}"],
        ['Total Pago:', f"R$ {total_pago:,.2f}"],
        ['Saldo Pendente:', f"R$ {total_devido:,.2f}"],
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
    
    elements.append(Paragraph("GestorCred - Sistema de Gestão de Empréstimos", footer_style))
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



@router.post("/{emprestimo_id}/amortizar")
async def amortizar_capital(
    emprestimo_id: str,
    payload: AmortizacaoRequest,
    request: Request,
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Amortiza capital de um empréstimo aberto (sem prazo + apenas_juros)
    
    - Reduz valor_principal do empréstimo
    - Registra um pagamento do tipo "amortizacao"
    - Se recalcular_juros=True: recalcula valor_juros/valor_total das parcelas
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
    
    valor_atual = float(emprestimo.get("valor_principal", 0))
    valor_amort = float(payload.valor_amortizacao)
    
    if valor_amort > valor_atual + 0.001:  # tolerância centavos
        raise HTTPException(
            status_code=400,
            detail=f"Valor da amortização (R$ {valor_amort:.2f}) maior que o capital devido (R$ {valor_atual:.2f})"
        )
    
    novo_principal = round(valor_atual - valor_amort, 2)
    data_pag = payload.data_pagamento or datetime.now(timezone.utc)
    
    # 1. Atualizar valor_principal do empréstimo
    await db.emprestimos.update_one(
        {"id": emprestimo_id, "usuario_id": context_id},
        {"$set": {"valor_principal": novo_principal}}
    )
    
    # 2. Registrar amortização como pagamento (tipo='amortizacao')
    import uuid as _uuid
    amort_doc = {
        "id": str(_uuid.uuid4()),
        "parcela_id": None,
        "emprestimo_id": emprestimo_id,
        "tipo": "amortizacao",
        "data_pagamento": data_pag.isoformat() if isinstance(data_pag, datetime) else data_pag,
        "valor_pago": valor_amort,
        "metodo_pagamento": payload.metodo_pagamento,
        "observacoes": payload.observacoes,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "usuario_id": context_id,
        "created_by": current_user.email,
        "cliente_id": emprestimo.get("cliente_id"),
        "cliente_nome": emprestimo.get("cliente_nome"),
        "valor_emprestimo": valor_atual,
        "principal_anterior": valor_atual,
        "principal_apos": novo_principal,
    }
    await db.pagamentos.insert_one(amort_doc)
    
    # 3. Recalcular juros das parcelas pendentes se solicitado
    parcelas_atualizadas = 0
    if payload.recalcular_juros and novo_principal > 0:
        periodicidade = emprestimo.get("periodicidade", "mensal")
        if periodicidade == "semanal":
            taxa_juros = emprestimo.get("taxa_juros_semanal", 0) or 0
        else:
            taxa_juros = emprestimo.get("taxa_juros_mensal", 0) or 0
        
        novo_juros = round(novo_principal * (taxa_juros / 100), 2)
        
        result_upd = await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
                "valor_pago": 0,  # só recalcular as que ainda nao tem pagamento parcial
            },
            {"$set": {
                "valor_juros": novo_juros,
                "valor_total": novo_juros,
                "saldo_devedor": novo_principal,
            }}
        )
        parcelas_atualizadas = result_upd.modified_count
        
        # Atualizar saldo_devedor das demais (parciais ou nao zeradas) tambem
        await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            },
            {"$set": {"saldo_devedor": novo_principal}}
        )
    else:
        # Mesmo sem recalcular juros, atualiza saldo_devedor (informativo)
        await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            },
            {"$set": {"saldo_devedor": novo_principal}}
        )
    
    # 4. Se capital chegou a zero -> quitar empréstimo
    quitado = False
    if novo_principal <= 0.0001:
        # Soft-cancel parcelas pendentes/atrasadas/parciais
        await db.parcelas.update_many(
            {
                "emprestimo_id": emprestimo_id,
                "usuario_id": context_id,
                "deleted": {"$ne": True},
                "status": {"$in": ["pendente", "atrasado", "parcial"]},
            },
            {"$set": {"deleted": True, "deleted_at": datetime.now(timezone.utc).isoformat(), "deleted_motivo": "Capital quitado por amortização total"}}
        )
        await db.emprestimos.update_one(
            {"id": emprestimo_id, "usuario_id": context_id},
            {"$set": {"status": "quitado"}}
        )
        quitado = True
    
    # 5. Auditoria
    await registrar_auditoria(
        usuario_id=context_id,
        usuario_email=current_user.email,
        acao="AMORTIZAR_CAPITAL",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
        detalhes=f"Amortização de R$ {valor_amort:.2f} no capital. {valor_atual:.2f} -> {novo_principal:.2f}. Recalcular: {payload.recalcular_juros}",
        dados_anteriores={"valor_principal": valor_atual},
        dados_novos={
            "valor_principal": novo_principal,
            "valor_amortizado": valor_amort,
            "recalculou_juros": payload.recalcular_juros,
            "parcelas_atualizadas": parcelas_atualizadas,
            "quitado": quitado,
        },
        ip=request.client.host if request.client else None,
        user_agent=request.headers.get("user-agent")
    )
    
    return {
        "message": "Amortização registrada com sucesso",
        "valor_amortizado": valor_amort,
        "principal_anterior": valor_atual,
        "principal_atual": novo_principal,
        "recalculou_juros": payload.recalcular_juros,
        "parcelas_atualizadas": parcelas_atualizadas,
        "quitado": quitado,
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
    from models.emprestimo import ProrrogacaoRequest, ProrrogacaoResponse
    from services.calculos import calcular_data_vencimento
    import uuid
    
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
        raise HTTPException(
            status_code=400,
            detail="Apenas empréstimos com método 'apenas_juros' podem ser prorrogados"
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
    if ultima_parcela.get("valor_principal", 0) == 0:
        raise HTTPException(
            status_code=400,
            detail="Última parcela não contém principal. Verifique o empréstimo."
        )
    
    # Obter dados do empréstimo
    valor_principal = emprestimo.get("valor_principal", 0)
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
    juros_periodo = valor_principal * (taxa_juros / 100)
    
    # Passo 1: Transformar última parcela em parcela de apenas juros
    await db.parcelas.update_one(
        {"id": ultima_parcela["id"]},
        {"$set": {
            "valor_principal": 0.0,
            "valor_juros": round(juros_periodo, 2),
            "valor_total": round(juros_periodo, 2),
            "saldo_devedor": valor_principal,
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
            "valor_principal": 0.0,
            "valor_juros": round(juros_periodo, 2),
            "valor_total": round(juros_periodo, 2),
            "valor_pago": 0.0,
            "valor_multa": 0.0,
            "valor_juros_mora": 0.0,
            "dias_atraso": 0,
            "saldo_devedor": valor_principal,
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
        "valor_principal": valor_principal,
        "valor_juros": round(juros_periodo, 2),
        "valor_total": round(valor_principal + juros_periodo, 2),
        "valor_pago": 0.0,
        "valor_multa": 0.0,
        "valor_juros_mora": 0.0,
        "dias_atraso": 0,
        "saldo_devedor": 0.0,
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
    
    await db.emprestimos.update_one(
        {"id": emprestimo_id},
        {"$set": update_emprestimo}
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
            "valor_total": p["valor_total"],
            "tipo": "apenas_juros" if p["valor_principal"] == 0 else "principal_juros"
        }
        for p in novas_parcelas
    ]
    
    return {
        "mensagem": f"Empréstimo prorrogado com sucesso por {periodos} {periodicidade}(s)",
        "emprestimo_id": emprestimo_id,
        "periodos_adicionados": periodos,
        "novo_total_parcelas": numero_ultima_nova,
        "novas_parcelas_criadas": novas_parcelas_info
    }

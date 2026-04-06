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
    SimulacaoRequest, SimulacaoResponse
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
    
    # Para empréstimos sem prazo, gerar apenas primeira parcela
    if emprestimo.sem_prazo:
        data_inicio = emprestimo.data_inicio or datetime.now(timezone.utc)
        
        # Calcular juros da primeira parcela baseado na periodicidade
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
        
        # Gerar PRIMEIRA parcela (apenas juros)
        from services.calculos import calcular_data_vencimento
        data_vencimento = calcular_data_vencimento(
            data_inicio, 
            1, 
            emprestimo.dia_vencimento, 
            emprestimo.periodicidade
        )
        
        primeira_parcela = Parcela(
            emprestimo_id=emprestimo_obj.id,
            numero_parcela=1,
            data_vencimento=data_vencimento,
            valor_principal=0.0,  # Apenas juros
            valor_juros=round(juros_periodo, 2),
            valor_total=round(juros_periodo, 2),
            saldo_devedor=emprestimo.valor_principal,
            total_parcelas=None  # Indeterminado
        )
        
        parcela_doc = primeira_parcela.model_dump()
        parcela_doc["data_vencimento"] = parcela_doc["data_vencimento"].isoformat()
        parcela_doc["created_at"] = parcela_doc["created_at"].isoformat()
        parcela_doc["usuario_id"] = context_id
        
        await db.parcelas.insert_one(parcela_doc)
        
        # Registrar auditoria
        await registrar_auditoria(
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            acao="CRIAR_EMPRESTIMO_ABERTO",
            entidade="emprestimos",
            entidade_id=emprestimo_obj.id,
            detalhes=f"Criou empréstimo aberto {periodicidade_label}: R$ {emprestimo.valor_principal:,.2f} - {emprestimo.metodo_calculo}",
            dados_novos={
                "valor_principal": emprestimo.valor_principal, 
                f"taxa_juros_{periodicidade_label}": taxa_juros, 
                "sem_prazo": True,
                "periodicidade": emprestimo.periodicidade
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
                {"emprestimo_id": e["id"]},
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
    
    # Verificar se existem parcelas pagas
    parcelas_pagas = await db.parcelas.count_documents({
        "emprestimo_id": emprestimo_id,
        "usuario_id": context_id,
        "status": "pago",
        "deleted": {"$ne": True}
    })
    
    # Campos que exigem recálculo de parcelas
    campos_financeiros = [
        "valor_principal", "taxa_juros_mensal", "prazo_meses", 
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
    
    # Se alterou financeiro, recalcular tudo
    if alterou_financeiro:
        # Preparar dados para simulação
        sim_data = {
            "valor_principal": updated_dict.get("valor_principal", emprestimo_original["valor_principal"]),
            "taxa_juros_mensal": updated_dict.get("taxa_juros_mensal", emprestimo_original["taxa_juros_mensal"]),
            "prazo_meses": updated_dict.get("prazo_meses", emprestimo_original["prazo_meses"]),
            "metodo_calculo": updated_dict.get("metodo_calculo", emprestimo_original["metodo_calculo"]),
            "periodo_carencia_meses": updated_dict.get("periodo_carencia_meses", emprestimo_original["periodo_carencia_meses"]),
            "taxa_multa_atraso": updated_dict.get("taxa_multa_atraso", emprestimo_original["taxa_multa_atraso"]),
            "taxa_juros_mora_diario": updated_dict.get("taxa_juros_mora_diario", emprestimo_original["taxa_juros_mora_diario"])
        }
        
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
        {"emprestimo_id": emprestimo_id},
        {"_id": 0}
    ).to_list(1000)
    
    valor_total_com_juros = sum(p["valor_total"] for p in todas_parcelas)
    valor_total_juros = valor_total_com_juros - emprestimo["valor_principal"]
    
    # Atualizar empréstimo
    await db.emprestimos.update_one(
        {"id": emprestimo_id},
        {"$set": {
            "valor_total_com_juros": round(valor_total_com_juros, 2),
            "valor_total_juros": round(valor_total_juros, 2),
            "prazo_meses": numero_proxima  # Define o prazo final
        }}
    )
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="QUITAR_EMPRESTIMO_ABERTO",
        entidade="emprestimos",
        entidade_id=emprestimo_id,
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
        "valor_total": round(emprestimo["valor_principal"] + juros_mensal, 2),
        "total_parcelas": numero_proxima,
        "valor_total_emprestimo": round(valor_total_com_juros, 2)
    }

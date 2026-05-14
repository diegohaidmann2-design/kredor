"""
Rotas de Clientes - Com Soft Delete e Paginação
"""
from fastapi import APIRouter, HTTPException, Depends, Request, Query
from typing import List, Optional
from datetime import datetime

from config import db
from models.cliente import Cliente, ClienteCreate, ClienteUpdate
from models.usuario import Usuario
from services.auth import get_current_user
from services.auditoria import registrar_auditoria
from services.permissao_service import verificar_pode_criar_cliente, verificar_plano_ativo
from services.soft_delete_service import soft_delete_cliente, restore_cliente, SoftDeleteService
from services.pagination_service import paginated_find, PaginationService
from services.logging_service import get_logger
from services.portal_service import PortalService
from services.auth_utils import get_user_context

router = APIRouter()
logger = get_logger("gestorcred.clientes")


@router.post("", response_model=Cliente)
async def criar_cliente(
    cliente: ClienteCreate,
    request: Request,
    current_user: Usuario = Depends(verificar_pode_criar_cliente)
):
    """Cria um novo cliente"""
    logger.info(f"Criando cliente para usuário {current_user.id}", data={"nome": cliente.nome})
    
    
    # Definir contexto (Dono)
    context_id = get_user_context(current_user)
    
    # Verificar se CPF/CNPJ já existe para este DONO (incluindo deletados)
    if cliente.cpf_cnpj:
        existing = await db.clientes.find_one({
            "cpf_cnpj": cliente.cpf_cnpj,
            "usuario_id": context_id,
            "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
        })
        if existing:
            raise HTTPException(status_code=400, detail="CPF/CNPJ já cadastrado")
    
    cliente_obj = Cliente(**cliente.model_dump())
    doc = cliente_obj.model_dump()
    doc["created_at"] = doc["created_at"].isoformat()
    doc["usuario_id"] = context_id  # Salvar como propriedade do DONO
    doc["created_by"] = current_user.email # Logar quem criou
    doc["deleted"] = False  # Marcar explicitamente como não deletado
    
    await db.clientes.insert_one(doc)
    
    # 🆕 GERAR CÓDIGO DE ACESSO DO PORTAL AUTOMATICAMENTE
    try:
        portal_service = PortalService(db)
        codigo = await portal_service.criar_ou_atualizar_codigo(
            cliente_id=cliente_obj.id,
            usuario_id=context_id
        )
        logger.info(f"Código de acesso do portal gerado", data={
            "cliente_id": cliente_obj.id,
            "codigo": codigo
        })
        
        # Enviar email com o código se o cliente tiver email
        if cliente.email:
            try:
                await portal_service.solicitar_codigo(
                    cliente.cpf_cnpj,
                    cliente.email
                )
                logger.info(f"Email com código enviado para o cliente", data={
                    "cliente_id": cliente_obj.id,
                    "email": cliente.email
                })
            except Exception as e:
                logger.warning(f"Erro ao enviar email com código", data={
                    "erro": str(e),
                    "cliente_id": cliente_obj.id
                })
    except Exception as e:
        logger.error(f"Erro ao gerar código de acesso do portal", data={
            "erro": str(e),
            "cliente_id": cliente_obj.id
        })
    
    # Registrar auditoria (Aqui mantemos current_user.id para saber QUEM fez)
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="criar",
        entidade="cliente",
        entidade_id=cliente_obj.id,
        detalhes=f"Criou cliente: {cliente.nome} - CPF/CNPJ: {cliente.cpf_cnpj} (Para: {context_id})",
        dados_novos={"nome": cliente.nome, "cpf_cnpj": cliente.cpf_cnpj},
        ip=request.client.host if request.client else None
    )
    
    # Notificação removida a pedido (redundante com feedback do frontend)
    # try:
    #     from services.notificacao_service import notificar_novo_cliente
    #     await notificar_novo_cliente(context_id, cliente.nome, cliente_obj.id)
    # except Exception as e:
    #     logger.warning(f"Erro ao criar notificação de cliente", data={"erro": str(e)})
    
    logger.info(f"Cliente criado com sucesso", data={"cliente_id": cliente_obj.id})
    return cliente_obj


@router.get("")
async def listar_clientes(
    status: Optional[str] = None,
    page: int = Query(1, ge=1, description="Número da página"),
    limit: int = Query(50, ge=1, le=100, description="Itens por página"),
    current_user: Usuario = Depends(verificar_plano_ativo)
):
    """
    Lista clientes do usuário com paginação
    
    Retorna:
    - items: Lista de clientes
    - pagination: Metadados de paginação (total, page, limit, pages, has_next, has_prev)
    """
    context_id = get_user_context(current_user)
    
    # Query base excluindo deletados
    query = SoftDeleteService.get_active_filter(context_id)
    
    if status:
        query["status"] = status
    
    # Usar paginação
    result = await paginated_find(
        db.clientes,
        query,
        page=page,
        limit=limit,
        sort_field="created_at",
        sort_direction=-1
    )
    
    # Converter datas
    for c in result["items"]:
        if "created_at" in c and isinstance(c["created_at"], str):
            c["created_at"] = datetime.fromisoformat(c["created_at"])
        
        # 🆕 Buscar código do portal se existir
        portal_auth = await db.portal_auth.find_one({"cliente_id": c["id"]})
        if portal_auth:
            c["codigo_portal"] = portal_auth.get("codigo_acesso")
        else:
            c["codigo_portal"] = None
    
    logger.debug(f"Listando clientes", data={"total": result["pagination"]["total"], "page": page})
    
    return result


@router.get("/lixeira")
async def listar_clientes_deletados(
    page: int = Query(1, ge=1),
    limit: int = Query(50, ge=1, le=100),
    current_user: Usuario = Depends(get_current_user)
):
    """Lista clientes na lixeira (soft deleted)"""
    context_id = get_user_context(current_user)
    result = await SoftDeleteService.list_deleted(
        "clientes",
        context_id,
        skip=(page - 1) * limit,
        limit=limit
    )
    
    return {
        "items": result["items"],
        "pagination": PaginationService.create_response(
            result["items"],
            result["total"],
            page,
            limit
        )["pagination"]
    }


@router.get("/{cliente_id}", response_model=Cliente)
async def obter_cliente(
    cliente_id: str,
    current_user: Usuario = Depends(get_current_user)
):
    """Obtém um cliente específico"""
    context_id = get_user_context(current_user)
    try:
        cliente = await db.clientes.find_one({
            "id": cliente_id,
            "usuario_id": context_id,
            "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
        }, {"_id": 0})
        
        if not cliente:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        
        # O modelo Cliente agora trata automaticamente a conversão de endereco e created_at
        return Cliente(**cliente)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Erro ao obter cliente {cliente_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao buscar cliente: {str(e)}")


@router.put("/{cliente_id}", response_model=Cliente)
async def atualizar_cliente(
    cliente_id: str,
    update_data: ClienteUpdate,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Atualiza um cliente"""
    context_id = get_user_context(current_user)
    cliente = await db.clientes.find_one({
        "id": cliente_id,
        "usuario_id": context_id,
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    }, {"_id": 0})
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    dados_anteriores = {"nome": cliente.get("nome"), "telefone": cliente.get("telefone")}
    
    update_dict = update_data.model_dump(exclude_unset=True)
    if update_dict:
        await db.clientes.update_one({"id": cliente_id}, {"$set": update_dict})
        
        # Registrar auditoria
        await registrar_auditoria(
            usuario_id=current_user.id,
            usuario_email=current_user.email,
            acao="editar",
            entidade="cliente",
            entidade_id=cliente_id,
            detalhes=f"Editou cliente: {cliente.get('nome')}",
            dados_anteriores=dados_anteriores,
            dados_novos=update_dict,
            ip=request.client.host if request.client else None
        )
        
        cliente.update(update_dict)
    
    cliente["created_at"] = datetime.fromisoformat(cliente["created_at"])
    return Cliente(**cliente)


@router.delete("/{cliente_id}")
async def deletar_cliente(
    cliente_id: str,
    request: Request,
    hard: bool = Query(False, description="Se True, deleta permanentemente"),
    current_user: Usuario = Depends(get_current_user)
):
    """
    Deleta um cliente (soft delete por padrão)
    
    - soft delete: Marca como deletado, pode ser restaurado
    - hard delete: Remove permanentemente (usar com cautela)
    """
    context_id = get_user_context(current_user)
    
    # Verificar se cliente pertence ao usuário
    # Se for hard delete, permitimos encontrar mesmo se já estiver marcado como deletado
    query = {"id": cliente_id, "usuario_id": context_id}
    if not hard:
        query["$or"] = [{"deleted": {"$exists": False}}, {"deleted": False}]
        
    cliente = await db.clientes.find_one(query)
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Verificar empréstimos ativos
    emprestimos = await db.emprestimos.find_one({
        "cliente_id": cliente_id,
        "usuario_id": context_id,
        "status": {"$in": ["ativo", "inadimplente"]},
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    })
    if emprestimos:
        raise HTTPException(status_code=400, detail="Cliente possui empréstimos ativos. Quite os empréstimos antes de deletar.")
    
    if hard:
        # Hard delete (remoção permanente)
        result = await db.clientes.delete_one({"id": cliente_id, "usuario_id": context_id})
        if result.deleted_count == 0:
            raise HTTPException(status_code=404, detail="Cliente não encontrado")
        action_msg = "deletado permanentemente"
    else:
        # Soft delete (padrão)
        success = await soft_delete_cliente(
            cliente_id,
            context_id,
            deleted_by=current_user.email,
            motivo="Deletado pelo usuário"
        )
        if not success:
            raise HTTPException(status_code=500, detail="Erro ao deletar cliente")
        action_msg = "movido para lixeira"
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="deletar" if hard else "soft_delete",
        entidade="cliente",
        entidade_id=cliente_id,
        detalhes=f"Cliente {action_msg}: {cliente.get('nome')}",
        dados_anteriores={"nome": cliente.get("nome"), "cpf_cnpj": cliente.get("cpf_cnpj")},
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Cliente {action_msg}", data={"cliente_id": cliente_id, "hard": hard})
    
    return {"message": f"Cliente {action_msg} com sucesso"}


@router.post("/{cliente_id}/restaurar")
async def restaurar_cliente(
    cliente_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Restaura um cliente da lixeira"""
    context_id = get_user_context(current_user)
    success = await restore_cliente(cliente_id, context_id)
    
    if not success:
        raise HTTPException(status_code=404, detail="Cliente não encontrado na lixeira")
    
    # Registrar auditoria
    await registrar_auditoria(
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="restaurar",
        entidade="cliente",
        entidade_id=cliente_id,
        detalhes=f"Cliente restaurado da lixeira",
        ip=request.client.host if request.client else None
    )
    
    logger.info(f"Cliente restaurado", data={"cliente_id": cliente_id})
    
    return {"message": "Cliente restaurado com sucesso"}


@router.post("/{cliente_id}/reenviar-codigo-portal")
async def reenviar_codigo_portal(
    cliente_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Reenvia o código de acesso do portal para o email do cliente"""
    # Buscar cliente
    context_id = get_user_context(current_user)
    cliente = await db.clientes.find_one({
        "id": cliente_id,
        "usuario_id": context_id,
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    })
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    if not cliente.get("email"):
        raise HTTPException(status_code=400, detail="Cliente não possui email cadastrado")
    
    # Buscar código do portal
    portal_auth = await db.portal_auth.find_one({"cliente_id": cliente_id})
    
    if not portal_auth:
        # Gerar código se não existir
        portal_service = PortalService(db)
        codigo = await portal_service.criar_ou_atualizar_codigo(cliente_id, context_id)
    
    # Enviar email
    try:
        portal_service = PortalService(db)
        await portal_service.solicitar_codigo(
            cliente.get("cpf_cnpj"),
            cliente.get("email")
        )
        
        logger.info(f"Código do portal reenviado", data={
            "cliente_id": cliente_id,
            "email": cliente.get("email")
        })
        
        return {"message": "Código enviado com sucesso para o email do cliente"}
    except Exception as e:
        logger.error(f"Erro ao reenviar código", data={"erro": str(e)})
        raise HTTPException(status_code=500, detail=f"Erro ao enviar email: {str(e)}")


@router.post("/{cliente_id}/gerar-codigo-portal")
async def gerar_codigo_portal(
    cliente_id: str,
    request: Request,
    current_user: Usuario = Depends(get_current_user)
):
    """Gera um código de acesso do portal para o cliente (mesmo sem email)"""
    # Buscar cliente
    context_id = get_user_context(current_user)
    cliente = await db.clientes.find_one({
        "id": cliente_id,
        "usuario_id": context_id,
        "$or": [{"deleted": {"$exists": False}}, {"deleted": False}]
    })
    
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado")
    
    # Gerar código
    portal_service = PortalService(db)
    codigo = await portal_service.criar_ou_atualizar_codigo(cliente_id, context_id)
    
    logger.info(f"Código do portal gerado manualmente", data={
        "cliente_id": cliente_id,
        "codigo": codigo
    })
    
    # Tentar enviar email se tiver
    email_enviado = False
    if cliente.get("email"):
        try:
            await portal_service.solicitar_codigo(
                cliente.get("cpf_cnpj"),
                cliente.get("email")
            )
            email_enviado = True
            logger.info(f"Email com código enviado", data={
                "cliente_id": cliente_id,
                "email": cliente.get("email")
            })
        except Exception as e:
            logger.warning(f"Erro ao enviar email", data={"erro": str(e)})
    
    return {
        "message": "Código gerado com sucesso",
        "codigo": codigo,
        "email_enviado": email_enviado
    }


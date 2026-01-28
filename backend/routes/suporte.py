from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from datetime import datetime
from models.suporte import *
from models.suporte import *
from services.suporte_service import SuporteService
from services.notificacao_service import criar_notificacao
from services.auth import get_current_user
from config import db

router = APIRouter()

# ========== ROTAS DO USUÁRIO ==========

@router.post("/tickets", response_model=dict)
async def criar_ticket(
    dados: CriarTicketRequest,
    current_user: dict = Depends(get_current_user)
):
    """Usuário cria um novo ticket"""
    ticket = await SuporteService.criar_ticket(
        usuario_id=current_user.id,
        usuario_nome=current_user.nome,
        usuario_email=current_user.email,
        dados=dados.dict()
    )
    
    return {
        "success": True,
        "ticket": ticket["numero_ticket"],
        "message": "Ticket criado com sucesso!"
    }

@router.get("/tickets", response_model=List[dict])
async def listar_meus_tickets(
    status: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Usuário lista seus próprios tickets"""
    
    query = {"usuario_id": current_user.id}
    if status:
        query["status"] = status
    
    tickets = await db.tickets_suporte.find(
        query,
        {"_id": 0}
    ).sort("atualizado_em", -1).to_list(100)
    
    return tickets

@router.get("/tickets/{numero_ticket}", response_model=dict)
async def visualizar_ticket(
    numero_ticket: str,
    current_user: dict = Depends(get_current_user)
):
    """Usuário visualiza detalhes de um ticket"""
    
    ticket = await db.tickets_suporte.find_one({
        "numero_ticket": numero_ticket,
        "usuario_id": current_user.id
    }, {"_id": 0})
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    # Marcar mensagens como lidas
    await SuporteService.marcar_mensagens_lidas(numero_ticket, "usuario")
    
    return ticket

@router.post("/tickets/{numero_ticket}/mensagens")
async def responder_ticket(
    numero_ticket: str,
    dados: ResponderTicketRequest,
    current_user: dict = Depends(get_current_user)
):
    """Usuário adiciona mensagem ao ticket"""
    
    # Verificar se o ticket pertence ao usuário
    ticket = await db.tickets_suporte.find_one({
        "numero_ticket": numero_ticket,
        "usuario_id": current_user.id
    })
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    if ticket["status"] == "fechado":
        raise HTTPException(status_code=400, detail="Ticket está fechado")
    
    mensagem = await SuporteService.adicionar_mensagem(
        numero_ticket=numero_ticket,
        remetente_id=current_user.id,
        remetente_nome=current_user.nome,
        remetente_tipo="usuario",
        conteudo=dados.mensagem,
        tipo=dados.tipo,
        arquivo_url=dados.arquivo_url
    )
    
    return {"success": True, "mensagem": mensagem}

# ========== ROTAS DO ADMIN ==========

@router.post("/admin/tickets", response_model=dict)
async def admin_criar_ticket(
    dados: CriarTicketAdminRequest,
    current_user: dict = Depends(get_current_user)
):
    """Admin cria um ticket em nome de um usuário"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    # Buscar dados do usuário
    usuario = await db.usuarios.find_one({"id": dados.usuario_id}) or await db.usuarios.find_one({"_id": dados.usuario_id})
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
        
    usuario_nome = usuario.get("nome", "Usuário")
    usuario_email = usuario.get("email", "")
    
    # Criar ticket
    ticket = await SuporteService.criar_ticket(
        usuario_id=dados.usuario_id,
        usuario_nome=usuario_nome,
        usuario_email=usuario_email,
        dados=dados.dict()
    )
    
    # Notificar o usuário
    await criar_notificacao(
        usuario_id=dados.usuario_id,
        tipo="suporte_novo",
        titulo=f"Novo ticket de suporte: {ticket['numero_ticket']}",
        mensagem=f"Um ticket foi aberto para você: {dados.assunto}",
        link=f"/suporte/{ticket['numero_ticket']}"
    )

    return {
        "success": True,
        "ticket": ticket["numero_ticket"],
        "message": "Ticket criado com sucesso!"
    }

@router.get("/admin/tickets", response_model=List[dict])
async def listar_todos_tickets(
    status: Optional[str] = None,
    categoria: Optional[str] = None,
    prioridade: Optional[str] = None,
    current_user: dict = Depends(get_current_user)
):
    """Admin lista todos os tickets"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    query = {}
    
    if status:
        query["status"] = status
    if categoria:
        query["categoria"] = categoria
    if prioridade:
        query["prioridade"] = prioridade
    
    tickets = await db.tickets_suporte.find(
        query,
        {"_id": 0, "mensagens": 0}  # Não trazer mensagens na listagem
    ).sort("atualizado_em", -1).to_list(100)
    
    return tickets

@router.get("/admin/tickets/{numero_ticket}", response_model=dict)
async def admin_visualizar_ticket(
    numero_ticket: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin visualiza detalhes de qualquer ticket"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    ticket = await db.tickets_suporte.find_one(
        {"numero_ticket": numero_ticket},
        {"_id": 0}
    )
    
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    # Marcar mensagens como lidas pelo admin
    await SuporteService.marcar_mensagens_lidas(numero_ticket, "admin")
    
    return ticket

@router.post("/admin/tickets/{numero_ticket}/mensagens")
async def admin_responder_ticket(
    numero_ticket: str,
    dados: ResponderTicketRequest,
    current_user: dict = Depends(get_current_user)
):
    """Admin responde um ticket"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    ticket = await db.tickets_suporte.find_one({"numero_ticket": numero_ticket})
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    mensagem = await SuporteService.adicionar_mensagem(
        numero_ticket=numero_ticket,
        remetente_id=current_user.id,
        remetente_nome=current_user.nome,
        remetente_tipo="admin",
        conteudo=dados.mensagem,
        tipo=dados.tipo,
        arquivo_url=dados.arquivo_url
    )
    
    return {"success": True, "mensagem": mensagem}

@router.put("/admin/tickets/{numero_ticket}/status")
async def admin_atualizar_status(
    numero_ticket: str,
    dados: AtualizarStatusRequest,
    current_user: dict = Depends(get_current_user)
):
    """Admin atualiza status do ticket"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    update = {
        "status": dados.status,
        "atualizado_em": datetime.now()
    }
    
    if dados.prioridade:
        update["prioridade"] = dados.prioridade
    
    result = await db.tickets_suporte.update_one(
        {"numero_ticket": numero_ticket},
        {"$set": update}
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    return {"success": True, "message": "Status atualizado"}

@router.put("/admin/tickets/{numero_ticket}/atribuir")
async def admin_atribuir_ticket(
    numero_ticket: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin atribui ticket a si mesmo"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    result = await db.tickets_suporte.update_one(
        {"numero_ticket": numero_ticket},
        {
            "$set": {
                "atribuido_a": current_user.id,
                "atribuido_nome": current_user.nome,
                "status": "em_atendimento",
                "atualizado_em": datetime.now()
            }
        }
    )
    
    if result.modified_count == 0:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
    
    return {"success": True, "message": "Ticket atribuído com sucesso"}

@router.delete("/admin/tickets/{numero_ticket}")
async def admin_deletar_ticket(
    numero_ticket: str,
    current_user: dict = Depends(get_current_user)
):
    """Admin remove um ticket permanentemente"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    sucesso = await SuporteService.deletar_ticket(numero_ticket)
    
    if not sucesso:
        raise HTTPException(status_code=404, detail="Ticket não encontrado")
        
    return {"success": True, "message": "Ticket removido com sucesso"}

@router.get("/admin/estatisticas")
async def estatisticas_suporte(
    current_user: dict = Depends(get_current_user)
):
    """Estatísticas do sistema de suporte"""
    if current_user.perfil != "admin":
        raise HTTPException(status_code=403, detail="Acesso negado")
    
    total = await db.tickets_suporte.count_documents({})
    abertos = await db.tickets_suporte.count_documents({"status": "aberto"})
    em_atendimento = await db.tickets_suporte.count_documents({"status": "em_atendimento"})
    resolvidos = await db.tickets_suporte.count_documents({"status": "resolvido"})
    
    return {
        "total": total,
        "abertos": abertos,
        "em_atendimento": em_atendimento,
        "resolvidos": resolvidos
    }

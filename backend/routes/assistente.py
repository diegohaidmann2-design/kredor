"""
Rotas do Assistente IA Interno (Sem LLM)
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import logging

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_recurso
from services.assistente_interno import assistente

router = APIRouter()


class AssistenteRequest(BaseModel):
    mensagem: str
    session_id: Optional[str] = None


class AssistenteResponse(BaseModel):
    resposta: str
    session_id: str


@router.post("/chat", response_model=AssistenteResponse)
async def chat_assistente(
    request: AssistenteRequest,
    current_user: Usuario = Depends(verificar_recurso("assistente_ia"))
):
    """Chat com o Assistente Interno (Sem LLM)"""
    try:
        session_id = request.session_id or f"{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Contexto do usuário
        context_id = get_user_context(current_user)
        total_clientes = await db.clientes.count_documents({"usuario_id": context_id})
        total_emprestimos = await db.emprestimos.count_documents({"usuario_id": context_id})
        emprestimos_ativos = await db.emprestimos.count_documents({
            "usuario_id": context_id,
            "status": "ativo"
        })
        
        contexto_usuario = {
            "nome": current_user.nome,
            "total_clientes": total_clientes,
            "total_emprestimos": total_emprestimos,
            "emprestimos_ativos": emprestimos_ativos
        }
        
        # Processar mensagem com assistente interno
        resposta = assistente.processar_mensagem(request.mensagem, contexto_usuario)
        
        # Salvar histórico
        await db.chat_historico.insert_one({
            "usuario_id": current_user.id,
            "session_id": session_id,
            "mensagem_usuario": request.mensagem,
            "resposta_ia": resposta,
            "tipo": "assistente_interno",
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return AssistenteResponse(resposta=resposta, session_id=session_id)
        
    except Exception as e:
        logging.error(f"Erro no assistente: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Erro ao processar mensagem: {str(e)}")


@router.get("/historico")
async def historico_chat(
    session_id: Optional[str] = None,
    current_user: Usuario = Depends(get_current_user)
):
    """Retorna histórico de conversas"""
    filtro = {"usuario_id": current_user.id}
    if session_id:
        filtro["session_id"] = session_id
    
    historico = await db.chat_historico.find(filtro, {"_id": 0}).sort("created_at", -1).limit(50).to_list(50)
    return historico

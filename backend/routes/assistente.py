"""
Rotas do Assistente IA
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timezone
import uuid
import os
import logging

from config import db, EMERGENT_LLM_KEY
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.permissao_service import verificar_recurso

# Import LLM
import google.generativeai as genai

router = APIRouter()


class AssistenteRequest(BaseModel):
    mensagem: str
    session_id: Optional[str] = None


class AssistenteResponse(BaseModel):
    resposta: str
    session_id: str


SYSTEM_MESSAGE = """Você é o Assistente IA do Gestor Cred - Sistema de Gestão de Empréstimos a Juros.

Você ajuda usuários a:
- Entender cálculos de juros (Simples, Compostos, Tabela Price, SAC)
- Gerenciar clientes e empréstimos
- Interpretar relatórios financeiros
- Configurar o sistema
- Resolver dúvidas sobre inadimplência e cobrança

Seja conciso, profissional e sempre ofereça exemplos práticos quando possível.
Use formatação clara com bullets e números quando listar informações.
Responda sempre em português brasileiro.

Contexto do sistema:
- Métodos de cálculo disponíveis: Juros Simples, Juros Compostos, Tabela Price e SAC
- O sistema permite cadastro de clientes com validação de CPF/CNPJ
- Empréstimos geram parcelas automaticamente com base no método escolhido
- Multa por atraso padrão: 2%
- Juros de mora padrão: 0,033% ao dia (1% ao mês)
"""


@router.post("/chat", response_model=AssistenteResponse)
async def chat_assistente(
    request: AssistenteRequest,
    current_user: Usuario = Depends(verificar_recurso("assistente_ia"))  # Verifica acesso ao recurso
):
    """Chat com o Assistente IA"""
    try:
        session_id = request.session_id or f"{current_user.id}_{uuid.uuid4().hex[:8]}"
        
        # Contexto do usuário (Dono)
        context_id = get_user_context(current_user)
        total_clientes = await db.clientes.count_documents({"usuario_id": context_id})
        total_emprestimos = await db.emprestimos.count_documents({"usuario_id": context_id})
        emprestimos_ativos = await db.emprestimos.count_documents({
            "usuario_id": context_id,
            "status": "ativo"
        })
        
        contexto_usuario = f"""
Contexto do usuário atual:
- Nome: {current_user.nome}
- Total de clientes: {total_clientes}
- Total de empréstimos: {total_emprestimos}
- Empréstimos ativos: {emprestimos_ativos}
"""
        
        system_message = SYSTEM_MESSAGE + contexto_usuario
        
        # Inicializar chat
        # Inicializar chat
        api_key = EMERGENT_LLM_KEY
        
        # Verificar configuração no banco
        config_ia = await db.configuracoes.find_one({"tipo": "ia"})
        if config_ia and config_ia.get("dados"):
            dados_ia = config_ia["dados"]
            # Se tiver chave no banco, usa ela (prioridade)
            if dados_ia.get("api_key"):
                api_key = dados_ia.get("api_key")
            
            # Se estiver desabilitado no banco, bloquear
            if dados_ia.get("habilitado") is False:
                raise HTTPException(status_code=403, detail="Assistente IA está desabilitado pelo administrador")

        if not api_key:
            raise HTTPException(status_code=500, detail="Chave da API não configurada")
        
        genai.configure(api_key=api_key)
        
        # Recuperar histórico recente (últimas 10 interações)
        historico_msgs = await db.chat_historico.find(
            {"session_id": session_id}
        ).sort("created_at", -1).limit(10).to_list(10)
        
        # Reordenar para cronológico
        historico_msgs.reverse()
        
        # Converter para formato do Gemini
        history = []
        for msg in historico_msgs:
            if "mensagem_usuario" in msg:
                history.append({"role": "user", "parts": [msg["mensagem_usuario"]]})
            if "resposta_ia" in msg:
                history.append({"role": "model", "parts": [msg["resposta_ia"]]})
        
        # Configurar modelo com instrução de sistema
        model = genai.GenerativeModel(
            model_name="gemini-1.5-flash",
            system_instruction=system_message
        )
        
        chat = model.start_chat(history=history)
        
        # Enviar mensagem
        response = await chat.send_message_async(request.mensagem)
        resposta = response.text
        
        # Salvar histórico
        await db.chat_historico.insert_one({
            "usuario_id": current_user.id,
            "session_id": session_id,
            "mensagem_usuario": request.mensagem,
            "resposta_ia": resposta,
            "created_at": datetime.now(timezone.utc).isoformat()
        })
        
        return AssistenteResponse(resposta=resposta, session_id=session_id)
        
    except Exception as e:
        logging.error(f"Erro no assistente IA: {str(e)}")
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

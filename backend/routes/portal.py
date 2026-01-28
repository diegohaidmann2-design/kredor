"""
Rotas do Portal do Cliente (Self-Service)
"""
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import List, Dict, Any
from datetime import datetime, timedelta, timezone
import jwt
import os

from config import db
from models.portal import (
    PortalLoginRequest, PortalLoginResponse,
    PortalSolicitarCodigoRequest, PortalAlterarCodigoRequest,
    PortalClienteInfo
)
from services.portal_service import PortalService

router = APIRouter(prefix="/portal", tags=["Portal do Cliente"])


def format_date(value) -> str:
    """Converte datetime ou string para string ISO format de forma segura"""
    if value is None:
        return None
    if isinstance(value, str):
        return value
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return str(value)


def parse_date(value) -> datetime:
    """Converte string ou datetime para datetime de forma segura"""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except:
            return None
    return None
security = HTTPBearer()

# Chave secreta para JWT do portal (diferente do JWT de usuários)
PORTAL_JWT_SECRET = os.getenv("JWT_SECRET_KEY", "your-secret-key-here") + "-portal"
PORTAL_JWT_ALGORITHM = "HS256"
PORTAL_JWT_EXPIRE_HOURS = 24


def criar_portal_token(cliente_id: str, usuario_id: str) -> str:
    """Cria token JWT para o portal do cliente"""
    payload = {
        "cliente_id": cliente_id,
        "usuario_id": usuario_id,
        "tipo": "portal",
        "exp": datetime.now(timezone.utc) + timedelta(hours=PORTAL_JWT_EXPIRE_HOURS),
        "iat": datetime.now(timezone.utc)
    }
    return jwt.encode(payload, PORTAL_JWT_SECRET, algorithm=PORTAL_JWT_ALGORITHM)


async def get_current_cliente(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> Dict[str, str]:
    """Dependency para obter cliente atual do token"""
    token = credentials.credentials
    
    try:
        payload = jwt.decode(token, PORTAL_JWT_SECRET, algorithms=[PORTAL_JWT_ALGORITHM])
        
        if payload.get("tipo") != "portal":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        cliente_id = payload.get("cliente_id")
        usuario_id = payload.get("usuario_id")
        
        if not cliente_id or not usuario_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido"
            )
        
        return {"cliente_id": cliente_id, "usuario_id": usuario_id}
    
    except jwt.ExpiredSignatureError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token expirado"
        )
    except jwt.InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token inválido"
        )


@router.post("/login", response_model=PortalLoginResponse)
async def portal_login(
    request: PortalLoginRequest
):
    """Login do cliente no portal"""
    service = PortalService(db)
    
    # Validar login
    result = await service.validar_login(request.cpf_cnpj, request.codigo_acesso)
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CPF/CNPJ ou código de acesso incorretos"
        )
    
    cliente = result["cliente"]
    usuario_id = result["usuario_id"]
    
    # Criar token
    token = criar_portal_token(cliente["id"], usuario_id)
    
    # Preparar dados do cliente
    cliente_data = {
        "id": cliente["id"],
        "nome": cliente["nome"],
        "cpf_cnpj": cliente["cpf_cnpj"],
        "telefone": cliente["telefone"],
        "email": cliente.get("email"),
        "status": cliente.get("status", "ativo")
    }
    
    return PortalLoginResponse(
        access_token=token,
        token_type="bearer",
        cliente=cliente_data
    )


@router.post("/solicitar-codigo")
async def solicitar_codigo(
    request: PortalSolicitarCodigoRequest
):
    """Solicita código de acesso por email"""
    service = PortalService(db)
    
    await service.solicitar_codigo(request.cpf_cnpj, request.email)
    
    return {
        "success": True,
        "message": "Código de acesso enviado para o email cadastrado"
    }


@router.get("/meu-perfil", response_model=PortalClienteInfo)
async def obter_meu_perfil(
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Obtém informações do perfil do cliente logado"""
    service = PortalService(db)
    return await service.obter_info_cliente(current["cliente_id"])


@router.get("/emprestimos")
async def listar_emprestimos(
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Lista empréstimos do cliente"""
    cliente_id = current["cliente_id"]
    
    emprestimos = await db["emprestimos"].find(
        {"cliente_id": cliente_id}
    ).sort("created_at", -1).to_list(None)
    
    # Adicionar informações de parcelas para cada empréstimo
    for emp in emprestimos:
        # Remover _id do MongoDB
        emp.pop("_id", None)
        
        # Buscar parcelas
        parcelas = await db["parcelas"].find(
            {"emprestimo_id": emp["id"]}
        ).sort("numero", 1).to_list(None)
        
        total_parcelas = len(parcelas)
        parcelas_pagas = sum(1 for p in parcelas if p.get("status") == "paga")
        parcelas_pendentes = total_parcelas - parcelas_pagas
        
        # Calcular valor total pago e restante
        valor_pago = sum(p.get("valor_pago", 0) for p in parcelas if p.get("status") == "paga")
        valor_restante = sum(p.get("valor", 0) for p in parcelas if p.get("status") == "pendente")
        
        emp["resumo_parcelas"] = {
            "total": total_parcelas,
            "pagas": parcelas_pagas,
            "pendentes": parcelas_pendentes,
            "valor_pago": valor_pago,
            "valor_restante": valor_restante
        }
        
        # Converter datas para string de forma segura
        emp["created_at"] = format_date(emp.get("created_at"))
        emp["data_primeiro_vencimento"] = format_date(emp.get("data_primeiro_vencimento"))
    
    return {
        "success": True,
        "emprestimos": emprestimos
    }


@router.get("/emprestimo/{emprestimo_id}")
async def obter_detalhes_emprestimo(
    emprestimo_id: str,
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Obtém detalhes de um empréstimo específico"""
    cliente_id = current["cliente_id"]
    
    # Buscar empréstimo
    emprestimo = await db["emprestimos"].find_one({
        "id": emprestimo_id,
        "cliente_id": cliente_id
    })
    
    if not emprestimo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado"
        )
    
    # Remover _id do MongoDB
    emprestimo.pop("_id", None)
    
    # Buscar parcelas
    parcelas = await db["parcelas"].find(
        {"emprestimo_id": emprestimo_id}
    ).sort("numero", 1).to_list(None)
    
    # Converter datas para string e remover _id
    for parcela in parcelas:
        parcela.pop("_id", None)
        parcela["data_vencimento"] = format_date(parcela.get("data_vencimento"))
        parcela["data_pagamento"] = format_date(parcela.get("data_pagamento"))
        
        # Calcular dias de atraso
        if parcela.get("status") == "pendente" and parcela.get("data_vencimento"):
            vencimento = parse_date(parcela["data_vencimento"])
            if vencimento:
                dias_atraso = (datetime.now(timezone.utc) - vencimento).days
                parcela["dias_atraso"] = max(0, dias_atraso)
    
    # Converter datas do empréstimo de forma segura
    emprestimo["created_at"] = format_date(emprestimo.get("created_at"))
    emprestimo["data_primeiro_vencimento"] = format_date(emprestimo.get("data_primeiro_vencimento"))
    
    return {
        "success": True,
        "emprestimo": emprestimo,
        "parcelas": parcelas
    }


@router.get("/emprestimo/{emprestimo_id}/historico-pagamentos")
async def obter_historico_pagamentos(
    emprestimo_id: str,
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Obtém histórico de pagamentos de um empréstimo"""
    cliente_id = current["cliente_id"]
    
    # Verificar se empréstimo pertence ao cliente
    emprestimo = await db["emprestimos"].find_one({
        "id": emprestimo_id,
        "cliente_id": cliente_id
    })
    
    if not emprestimo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empréstimo não encontrado"
        )
    
    # Buscar pagamentos
    pagamentos = await db["pagamentos"].find(
        {"emprestimo_id": emprestimo_id}
    ).sort("data_pagamento", -1).to_list(None)
    
    # Converter datas de forma segura e remover _id
    for pag in pagamentos:
        pag.pop("_id", None)
        pag["data_pagamento"] = format_date(pag.get("data_pagamento"))
        pag["created_at"] = format_date(pag.get("created_at"))
    
    return {
        "success": True,
        "pagamentos": pagamentos
    }


@router.put("/alterar-codigo")
async def alterar_codigo(
    request: PortalAlterarCodigoRequest,
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Altera o código de acesso do cliente"""
    cliente_id = current["cliente_id"]
    
    # Validar se os códigos novos são iguais
    if request.codigo_novo != request.codigo_novo_confirmacao:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Os códigos novos não conferem"
        )
    
    service = PortalService(db)
    await service.alterar_codigo(cliente_id, request.codigo_atual, request.codigo_novo)
    
    return {
        "success": True,
        "message": "Código de acesso alterado com sucesso"
    }


@router.get("/proximas-parcelas")
async def obter_proximas_parcelas(
    current: Dict[str, str] = Depends(get_current_cliente)
):
    """Obtém próximas parcelas a vencer do cliente"""
    cliente_id = current["cliente_id"]
    
    # Buscar empréstimos do cliente
    emprestimos = await db["emprestimos"].find(
        {"cliente_id": cliente_id}
    ).to_list(None)
    
    if not emprestimos:
        return {
            "success": True,
            "parcelas": []
        }
    
    emprestimo_ids = [e["id"] for e in emprestimos]
    
    # Buscar próximas 5 parcelas pendentes
    parcelas = await db["parcelas"].find({
        "emprestimo_id": {"$in": emprestimo_ids},
        "status": "pendente"
    }).sort("data_vencimento", 1).limit(5).to_list(None)
    
    # Adicionar informações do empréstimo em cada parcela
    emprestimos_dict = {e["id"]: e for e in emprestimos}
    
    for parcela in parcelas:
        # Remover _id do MongoDB
        parcela.pop("_id", None)
        
        emp = emprestimos_dict.get(parcela["emprestimo_id"])
        if emp:
            parcela["emprestimo_valor"] = emp.get("valor_principal")
            parcela["emprestimo_metodo"] = emp.get("metodo_calculo")
        
        # Converter datas de forma segura
        vencimento_raw = parcela.get("data_vencimento")
        vencimento = parse_date(vencimento_raw)
        parcela["data_vencimento"] = format_date(vencimento_raw)
        
        # Calcular dias até vencimento
        if vencimento:
            dias_ate = (vencimento - datetime.now(timezone.utc)).days
            parcela["dias_ate_vencimento"] = dias_ate
            
            # Status de urgência
            if dias_ate < 0:
                parcela["urgencia"] = "atrasada"
            elif dias_ate <= 3:
                parcela["urgencia"] = "urgente"
            elif dias_ate <= 7:
                parcela["urgencia"] = "proxima"
            else:
                parcela["urgencia"] = "normal"
        else:
            parcela["dias_ate_vencimento"] = 0
            parcela["urgencia"] = "normal"
    
    return {
        "success": True,
        "parcelas": parcelas
    }

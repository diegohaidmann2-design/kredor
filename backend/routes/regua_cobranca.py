"""Rotas da Régua de Cobrança automática via WhatsApp."""
from typing import List, Optional

from fastapi import APIRouter, Depends

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services import regua_cobranca_service as regua
from utils.dinheiro import EntradaEmReais

router = APIRouter()


class ReguaConfigUpdate(EntradaEmReais):
    """Configuração da régua enviada pela tela.

    Antes a rota recebia `dict` cru enquanto a resposta já convertia centavos em reais pelo
    ReaisJSONResponse — a rota era assimétrica, e um campo de dinheiro entraria em centavos
    errados. Com o modelo, a tela manda `valor_minimo` em reais e aqui chega em centavos (R6).
    """
    ativo: Optional[bool] = None
    lembrete_ativo: Optional[bool] = None
    lembrete_dias_antes: Optional[List[int]] = None
    vencimento_ativo: Optional[bool] = None
    atraso_ativo: Optional[bool] = None
    atraso_dias: Optional[List[int]] = None
    usar_fila: Optional[bool] = None
    valor_minimo_centavos: Optional[int] = None


@router.get("/regua/config")
async def obter_config_regua(current_user: Usuario = Depends(get_current_user)):
    return await regua.get_config(current_user.id)


@router.put("/regua/config")
async def atualizar_config_regua(
    dados: ReguaConfigUpdate,
    current_user: Usuario = Depends(get_current_user),
):
    # exclude_none: campo ausente no PUT mantém o padrão, como já era com o dict.
    return await regua.salvar_config(current_user.id, dados.model_dump(exclude_none=True))


@router.post("/regua/executar")
async def executar_regua_agora(current_user: Usuario = Depends(get_current_user)):
    """Executa a régua imediatamente para o usuário logado (ignora o flag ativo)."""
    stats = await regua.processar_regua(current_user.id, forcar=True)
    return {"success": True, "stats": stats}


@router.get("/regua/historico")
async def historico_regua(limit: int = 50, current_user: Usuario = Depends(get_current_user)):
    itens = await db.regua_envios.find(
        {"usuario_id": current_user.id}
    ).sort("created_at", -1).limit(limit).to_list(limit)
    for it in itens:
        it["_id"] = str(it["_id"])
    return {"itens": itens, "total": len(itens)}

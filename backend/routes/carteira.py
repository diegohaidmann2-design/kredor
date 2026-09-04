"""
Rotas da Carteira de Consultas (usuário).
- GET  /api/carteira/               -> resumo (saldo + precos + últimos movimentos)
- GET  /api/carteira/precos         -> tabela pública de preços ativos
- GET  /api/carteira/movimentos     -> lista paginada de movimentos
- POST /api/carteira/recarga/asaas  -> gera cobrança PIX de recarga (Asaas)
- POST /api/carteira/recarga/syncpay-> gera cobrança PIX de recarga (SyncPay)
- GET  /api/carteira/gateways       -> lista gateways disponíveis
"""
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from config import db
from models.usuario import Usuario
from services.auth import get_current_user
from services.auth_utils import get_user_context
from services.carteira_service import (
    obter_ou_criar_carteira, listar_precos, listar_movimentos,
    creditar_recarga,  # não usado direto aqui, mas útil p/ tests
)
from services.asaas_service import asaas_service
from services.syncpay import obter_syncpay_service

router = APIRouter()

VALOR_MINIMO_RECARGA = 5.00
VALOR_MAXIMO_RECARGA = 5000.00


class RecargaRequest(BaseModel):
    valor: float = Field(..., ge=VALOR_MINIMO_RECARGA, le=VALOR_MAXIMO_RECARGA)


def _validar_valor(valor: float) -> float:
    v = round(float(valor), 2)
    if v < VALOR_MINIMO_RECARGA:
        raise HTTPException(status_code=400, detail=f"Valor mínimo de recarga: R$ {VALOR_MINIMO_RECARGA:,.2f}")
    if v > VALOR_MAXIMO_RECARGA:
        raise HTTPException(status_code=400, detail=f"Valor máximo de recarga: R$ {VALOR_MAXIMO_RECARGA:,.2f}")
    return v


@router.get("/")
async def resumo(current_user: Usuario = Depends(get_current_user)):
    """Resumo da carteira do dono do usuário atual."""
    owner_id = get_user_context(current_user)
    carteira = await obter_ou_criar_carteira(owner_id)
    precos = await listar_precos(apenas_ativos=True)
    movs = await listar_movimentos(owner_id, limit=10, skip=0)
    return {
        "carteira": carteira,
        "precos": precos,
        "ultimos_movimentos": movs["itens"],
        "pacotes_sugeridos": [20, 50, 100, 200, 500],
    }


@router.get("/precos")
async def precos(current_user: Usuario = Depends(get_current_user)):
    return {"itens": await listar_precos(apenas_ativos=True)}


@router.get("/movimentos")
async def movimentos(
    limit: int = Query(50, ge=1, le=200),
    skip: int = Query(0, ge=0),
    tipo: str = Query(None),
    current_user: Usuario = Depends(get_current_user),
):
    owner_id = get_user_context(current_user)
    return await listar_movimentos(owner_id, limit=limit, skip=skip, tipo=tipo)


@router.get("/gateways")
async def gateways_disponiveis(current_user: Usuario = Depends(get_current_user)):
    """Retorna quais gateways estão ativos no sistema para recarga PIX."""
    cfg = await db.configuracoes.find_one({"tipo": "assinatura_gateway"})
    dados = (cfg or {}).get("dados") or {}
    return {
        "asaas": bool(dados.get("asaas_habilitado")) and bool(dados.get("asaas_api_key")),
        "syncpay": bool(dados.get("syncpay_habilitado")) and bool(dados.get("syncpay_client_id")),
    }


@router.post("/recarga/asaas")
async def recarga_asaas(body: RecargaRequest, current_user: Usuario = Depends(get_current_user)):
    """Gera cobrança PIX no Asaas para recarga da carteira."""
    owner_id = get_user_context(current_user)
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da conta pode recarregar a carteira.")

    valor = _validar_valor(body.valor)
    await obter_ou_criar_carteira(owner_id)

    # 1) Obter/criar customer Asaas
    dono = await db.usuarios.find_one({"id": owner_id}, {"_id": 0})
    if not dono:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    customer_id = dono.get("asaas_customer_id")
    if not customer_id:
        cpf_cnpj = dono.get("cpf") or dono.get("cnpj") or "00000000000"
        try:
            customer = await asaas_service.criar_cliente(
                nome=dono.get("nome") or "Cliente",
                email=dono.get("email"),
                cpf_cnpj=cpf_cnpj,
                telefone=dono.get("telefone"),
            )
            customer_id = customer.get("id")
            await db.usuarios.update_one(
                {"id": owner_id}, {"$set": {"asaas_customer_id": customer_id}}
            )
        except Exception as e:
            raise HTTPException(status_code=502, detail=f"Falha ao configurar cliente no Asaas: {str(e)}")

    # 2) Criar cobrança PIX (vencimento hoje)
    externo = f"carteira_recarga_{owner_id}_{uuid.uuid4().hex[:12]}"
    hoje = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        payload = {
            "customer": customer_id,
            "billingType": "PIX",
            "value": valor,
            "dueDate": hoje,
            "description": f"Recarga Carteira Consultas — R$ {valor:,.2f}",
            "externalReference": externo,
            "postalService": False,
        }
        import httpx
        headers = await asaas_service._get_headers()
        base_url = await asaas_service._get_base_url()
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(f"{base_url}/payments", headers=headers, json=payload)
            if resp.status_code not in (200, 201):
                raise HTTPException(status_code=502, detail=f"Asaas: {resp.text}")
            cobranca = resp.json()
        payment_id = cobranca.get("id")

        # 3) QR Code PIX
        qr = await asaas_service.obter_qrcode_pix(payment_id)
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao criar cobrança PIX: {str(e)}")

    # 4) Registrar transação pendente
    await db.carteira_recargas.insert_one({
        "id": externo,
        "owner_id": owner_id,
        "gateway": "asaas",
        "payment_id": payment_id,
        "valor": valor,
        "status": "pending",
        "external_reference": externo,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": cobranca,
    })

    return {
        "recarga_id": externo,
        "payment_id": payment_id,
        "gateway": "asaas",
        "valor": valor,
        "status": "pending",
        "pix": {
            "qrcode_image": qr.get("encodedImage"),
            "payload": qr.get("payload"),
            "expira_em": qr.get("expirationDate"),
        },
        "invoice_url": cobranca.get("invoiceUrl"),
    }


@router.post("/recarga/syncpay")
async def recarga_syncpay(body: RecargaRequest, current_user: Usuario = Depends(get_current_user)):
    """Gera cobrança PIX no SyncPay para recarga."""
    owner_id = get_user_context(current_user)
    if owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Apenas o dono da conta pode recarregar a carteira.")

    valor = _validar_valor(body.valor)
    await obter_ou_criar_carteira(owner_id)

    dono = await db.usuarios.find_one({"id": owner_id}, {"_id": 0})
    if not dono:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    service = await obter_syncpay_service()
    if not service:
        raise HTTPException(status_code=503, detail="SyncPay não está habilitado.")

    external_id = f"carteira_recarga_{owner_id}_{uuid.uuid4().hex[:12]}"
    try:
        cobranca = await service.criar_cobranca_pix(
            valor=valor,
            descricao=f"Recarga Carteira Consultas — R$ {valor:,.2f}",
            external_id=external_id,
            customer_name=dono.get("nome"),
            customer_email=dono.get("email"),
            customer_cpf=dono.get("cpf"),
            customer_phone=dono.get("telefone"),
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"Erro ao criar PIX no SyncPay: {str(e)}")

    payment_id = cobranca.get("identifier")
    await db.carteira_recargas.insert_one({
        "id": external_id,
        "owner_id": owner_id,
        "gateway": "syncpay",
        "payment_id": payment_id,
        "valor": valor,
        "status": "pending",
        "external_reference": external_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "raw": cobranca,
    })

    return {
        "recarga_id": external_id,
        "payment_id": payment_id,
        "gateway": "syncpay",
        "valor": valor,
        "status": "pending",
        "pix": {"payload": cobranca.get("pix_code")},
    }


@router.get("/recarga/{recarga_id}/status")
async def status_recarga(
    recarga_id: str,
    current_user: Usuario = Depends(get_current_user),
):
    """Consulta status de uma recarga (útil para o frontend fazer polling)."""
    owner_id = get_user_context(current_user)
    doc = await db.carteira_recargas.find_one(
        {"id": recarga_id, "owner_id": owner_id}, {"_id": 0, "raw": 0}
    )
    if not doc:
        raise HTTPException(status_code=404, detail="Recarga não encontrada.")

    # Se ainda pending, tenta consultar no gateway para atualizar mais rápido
    if doc.get("status") == "pending":
        try:
            if doc.get("gateway") == "asaas":
                cobranca = await asaas_service.buscar_cobranca(doc["payment_id"])
                gw_status = (cobranca.get("status") or "").upper()
                if gw_status in ("RECEIVED", "CONFIRMED", "RECEIVED_IN_CASH"):
                    # Creditar
                    mov = await creditar_recarga(
                        owner_id=owner_id, valor=float(doc["valor"]),
                        gateway="asaas", payment_id=doc["payment_id"],
                        metadata={"recarga_id": recarga_id},
                    )
                    await db.carteira_recargas.update_one(
                        {"id": recarga_id},
                        {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
                    )
                    doc["status"] = "paid"
            elif doc.get("gateway") == "syncpay":
                service = await obter_syncpay_service()
                if service and doc.get("payment_id"):
                    tx = await service.consultar_transacao(doc["payment_id"])
                    if (tx.get("status") or "").lower() == "completed":
                        await creditar_recarga(
                            owner_id=owner_id, valor=float(doc["valor"]),
                            gateway="syncpay", payment_id=doc["payment_id"],
                            metadata={"recarga_id": recarga_id},
                        )
                        await db.carteira_recargas.update_one(
                            {"id": recarga_id},
                            {"$set": {"status": "paid", "paid_at": datetime.now(timezone.utc).isoformat()}}
                        )
                        doc["status"] = "paid"
        except Exception as e:
            # Falha silenciosa; polling volta na próxima
            print(f"[carteira] polling recarga erro: {e}")

    return doc

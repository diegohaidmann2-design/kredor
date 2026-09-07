"""
Painel de Segurança (Admin)
Expõe: contas bloqueadas por brute force, IPs bloqueados e eventos de
webhook suspeitos — para monitoramento quase em tempo real.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from datetime import datetime, timezone

from config import db
from services.auth import require_admin

router = APIRouter(dependencies=[Depends(require_admin)])


def _parse_dt(value):
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except ValueError:
            return None
    return value


def _bloqueio_ativo(bloqueado_ate) -> bool:
    dt = _parse_dt(bloqueado_ate)
    if not dt:
        return False
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return datetime.now(timezone.utc) < dt


@router.get("/resumo")
async def resumo_seguranca():
    """Contadores para os cards do painel."""
    agora = datetime.now(timezone.utc).isoformat()
    contas_bloqueadas = await db.login_attempts.count_documents(
        {"bloqueado_ate": {"$gt": agora}}
    )
    ips_bloqueados = await db.login_attempts_ip.count_documents(
        {"bloqueado_ate": {"$gt": agora}}
    )
    tentativas_ativas = await db.login_attempts.count_documents({"tentativas": {"$gte": 1}})
    webhooks_suspeitos_24h = await db.security_logs.count_documents({
        "event_type": "webhook_suspeito",
    })
    return {
        "contas_bloqueadas": contas_bloqueadas,
        "ips_bloqueados": ips_bloqueados,
        "tentativas_ativas": tentativas_ativas,
        "webhooks_suspeitos": webhooks_suspeitos_24h,
        "atualizado_em": agora,
    }


@router.get("/login-bloqueios")
async def login_bloqueios(limit: int = Query(100, ge=1, le=500)):
    """Tentativas de login por conta (e-mail) e por IP, com estado de bloqueio."""
    contas = []
    cursor = db.login_attempts.find({}, {"_id": 0}).sort("ultima_tentativa", -1).limit(limit)
    async for doc in cursor:
        contas.append({
            "email": doc.get("email"),
            "tentativas": doc.get("tentativas", 0),
            "ip": doc.get("ip"),
            "ultima_tentativa": doc.get("ultima_tentativa"),
            "bloqueado_ate": doc.get("bloqueado_ate"),
            "bloqueado": _bloqueio_ativo(doc.get("bloqueado_ate")),
        })

    ips = []
    cursor_ip = db.login_attempts_ip.find({}, {"_id": 0}).sort("ultima_tentativa", -1).limit(limit)
    async for doc in cursor_ip:
        ips.append({
            "ip": doc.get("ip"),
            "tentativas": doc.get("tentativas", 0),
            "ultima_tentativa": doc.get("ultima_tentativa"),
            "bloqueado_ate": doc.get("bloqueado_ate"),
            "bloqueado": _bloqueio_ativo(doc.get("bloqueado_ate")),
        })

    return {"contas": contas, "ips": ips}


@router.get("/webhooks-suspeitos")
async def webhooks_suspeitos(limit: int = Query(50, ge=1, le=200)):
    """Eventos de webhook rejeitados/suspeitos registrados."""
    itens = []
    cursor = db.security_logs.find(
        {"event_type": "webhook_suspeito"}, {"_id": 0}
    ).sort("created_at", -1).limit(limit)
    async for doc in cursor:
        itens.append({
            "descricao": doc.get("description"),
            "ip": doc.get("ip_address"),
            "severity": doc.get("severity"),
            "detalhes": doc.get("details", {}),
            "created_at": doc.get("created_at"),
        })
    return {"itens": itens, "total": len(itens)}


@router.post("/desbloquear-conta")
async def desbloquear_conta(email: str = Query(...)):
    res = await db.login_attempts.delete_one({"email": email})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nenhum bloqueio encontrado para este e-mail")
    return {"message": f"Bloqueio da conta {email} removido"}


@router.post("/desbloquear-ip")
async def desbloquear_ip(ip: str = Query(...)):
    res = await db.login_attempts_ip.delete_one({"ip": ip})
    if res.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Nenhum bloqueio encontrado para este IP")
    return {"message": f"Bloqueio do IP {ip} removido"}

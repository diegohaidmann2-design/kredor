"""Régua de cobrança automática via WhatsApp.

Varre as parcelas em aberto de um usuário e enfileira mensagens conforme a
configuração (lembrete antes do vencimento, cobrança no dia e cobrança de
atraso), respeitando o anti-spam/horário comercial (via fila) e evitando
envios duplicados (coleção `regua_envios`).
"""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from config import db
from utils.dinheiro import formatar_reais
from services.whatsapp_fila_service import WhatsAppFilaService
from services.whatsapp_service import formatar_template_mensagem
from services.whatsapp_service import enviar_mensagem_whatsapp

TZ = ZoneInfo("America/Sao_Paulo")

DEFAULT_CONFIG = {
    "ativo": False,
    "lembrete_ativo": True,
    "lembrete_dias_antes": [3, 1],
    "vencimento_ativo": True,
    "atraso_ativo": True,
    "atraso_dias": [1, 3, 7, 15],
    "usar_fila": True,
}

CAMPOS_PERMITIDOS = set(DEFAULT_CONFIG.keys())

TEMPLATES_PADRAO = {
    "lembrete": (
        "Olá {cliente_nome}! 👋\n\n"
        "Passando para lembrar da sua parcela {numero_parcela}/{total_parcelas}:\n"
        "📅 Vencimento: {data_vencimento}\n"
        "💰 Valor: R$ {valor}\n\n"
        "Qualquer dúvida, estou à disposição!"
    ),
    "cobranca": (
        "Olá {cliente_nome}! 👋\n\n"
        "Sua parcela {numero_parcela}/{total_parcelas} vence hoje:\n"
        "📅 Vencimento: {data_vencimento}\n"
        "💰 Valor: R$ {valor}\n\n"
        "Conto com você. Obrigado!"
    ),
    "atraso": (
        "Olá {cliente_nome}! ⚠️\n\n"
        "A parcela {numero_parcela}/{total_parcelas} está em atraso há {dias} dia(s).\n"
        "💰 Valor: R$ {valor}\n"
        "📅 Vencimento: {data_vencimento}\n\n"
        "Por favor, regularize para evitar acréscimos. Estou à disposição para negociar!"
    ),
}


async def get_config(usuario_id: str) -> dict:
    doc = await db.configuracoes.find_one({"tipo": "regua_cobranca", "usuario_id": usuario_id})
    dados = (doc or {}).get("dados", {}) or {}
    return {**DEFAULT_CONFIG, **dados}


async def salvar_config(usuario_id: str, dados: dict) -> dict:
    limpo = {}
    for k, v in (dados or {}).items():
        if k not in CAMPOS_PERMITIDOS:
            continue
        if k in ("lembrete_dias_antes", "atraso_dias"):
            try:
                v = sorted({int(x) for x in v if int(x) >= 0})
            except Exception:
                v = DEFAULT_CONFIG[k]
        elif k in ("ativo", "lembrete_ativo", "vencimento_ativo", "atraso_ativo", "usar_fila"):
            v = bool(v)
        limpo[k] = v

    cfg = {**DEFAULT_CONFIG, **limpo}
    await db.configuracoes.update_one(
        {"tipo": "regua_cobranca", "usuario_id": usuario_id},
        {"$set": {
            "tipo": "regua_cobranca",
            "usuario_id": usuario_id,
            "dados": cfg,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }},
        upsert=True,
    )
    return cfg


async def _get_template(usuario_id: str, tipo: str) -> str:
    t = await db.whatsapp_templates.find_one({"usuario_id": usuario_id, "tipo": tipo, "ativo": True})
    if not t:
        t = await db.whatsapp_templates.find_one({"tipo": tipo, "ativo": True})
    if t and t.get("mensagem"):
        return t["mensagem"]
    return TEMPLATES_PADRAO.get(tipo, "Olá {cliente_nome}!")


def _fmt_valor(centavos: int) -> str:
    return formatar_reais(centavos)


def _fmt_data(dv) -> str:
    try:
        dt = datetime.fromisoformat(str(dv).replace("Z", "+00:00"))
        return dt.strftime("%d/%m/%Y")
    except Exception:
        return str(dv)


def _telefone_cliente(cliente: dict):
    return cliente.get("telefone") or cliente.get("celular") or cliente.get("whatsapp")


async def processar_regua(usuario_id: str, hoje=None, forcar: bool = False, limite: int = 2000) -> dict:
    """Processa a régua para um usuário. `forcar=True` ignora o flag ativo."""
    cfg = await get_config(usuario_id)
    stats = {
        "lembrete": 0, "cobranca": 0, "atraso": 0,
        "enfileiradas": 0, "puladas_duplicadas": 0, "sem_telefone": 0,
    }

    if not forcar and not cfg.get("ativo"):
        stats["motivo"] = "regua_inativa"
        return stats

    agora = hoje or datetime.now(TZ)
    hoje_date = agora.date()
    fila = WhatsAppFilaService(db)

    cursor = db.parcelas.find({
        "usuario_id": usuario_id,
        "status": {"$in": ["pendente", "atrasado", "parcial"]},
        "deleted": {"$ne": True},
    }).limit(limite)

    emp_cache, cli_cache = {}, {}

    async for parc in cursor:
        dv = parc.get("data_vencimento")
        if not dv:
            continue
        try:
            venc_dt = datetime.fromisoformat(str(dv).replace("Z", "+00:00"))
            venc_date = venc_dt.astimezone(TZ).date() if venc_dt.tzinfo else venc_dt.date()
        except Exception:
            continue

        valor_devido = (parc.get("valor_total_centavos", 0) or 0) - (parc.get("valor_pago_centavos", 0) or 0)
        if valor_devido <= 0:
            continue

        diff = (hoje_date - venc_date).days  # <0 antes, 0 hoje, >0 atraso

        evento = tipo_template = None
        if cfg.get("lembrete_ativo") and diff < 0 and (-diff) in cfg.get("lembrete_dias_antes", []):
            evento, tipo_template = f"lembrete_{-diff}", "lembrete"
        elif cfg.get("vencimento_ativo") and diff == 0:
            evento, tipo_template = "vencimento", "cobranca"
        elif cfg.get("atraso_ativo") and diff > 0 and diff in cfg.get("atraso_dias", []):
            evento, tipo_template = f"atraso_{diff}", "atraso"

        if not evento:
            continue

        dedup = {"usuario_id": usuario_id, "parcela_id": parc["id"], "evento": evento}
        if await db.regua_envios.find_one(dedup):
            stats["puladas_duplicadas"] += 1
            continue

        emp_id = parc.get("emprestimo_id")
        if emp_id not in emp_cache:
            emp_cache[emp_id] = await db.emprestimos.find_one({"id": emp_id}) or {}
        emp = emp_cache[emp_id]

        cli_id = emp.get("cliente_id")
        if cli_id not in cli_cache:
            cli_cache[cli_id] = await db.clientes.find_one({"id": cli_id}) or {}
        cli = cli_cache[cli_id]

        telefone = _telefone_cliente(cli)
        if not telefone:
            stats["sem_telefone"] += 1
            continue

        template = await _get_template(usuario_id, tipo_template)
        mensagem = formatar_template_mensagem(template, {
            "cliente_nome": cli.get("nome", "Cliente"),
            "numero_parcela": str(parc.get("numero_parcela", "?")),
            "total_parcelas": str(parc.get("total_parcelas") or emp.get("prazo_meses") or "?"),
            "valor": _fmt_valor(valor_devido),
            "data_vencimento": _fmt_data(dv),
            "dias": str(max(diff, 0)),
        })

        if cfg.get("usar_fila", True):
            await fila.adicionar_na_fila(
                usuario_id=usuario_id,
                numero_destino=telefone,
                mensagem=mensagem,
                cliente_id=cli_id,
                emprestimo_id=emp_id,
                parcela_id=parc["id"],
                tipo=f"regua_{tipo_template}",
                prioridade=3 if tipo_template == "atraso" else 5,
            )
        else:
            await enviar_mensagem_whatsapp(usuario_id, telefone, mensagem)

        await db.regua_envios.insert_one({
            **dedup,
            "tipo": tipo_template,
            "numero_destino": telefone,
            "cliente_id": cli_id,
            "emprestimo_id": emp_id,
            "valor": valor_devido,
            "data_ref": hoje_date.isoformat(),
            "created_at": datetime.now(timezone.utc).isoformat(),
        })

        stats[tipo_template] += 1
        stats["enfileiradas"] += 1

    return stats


async def processar_regua_todos() -> dict:
    """Executa a régua para todos os usuários com régua ativa (usado pelo scheduler)."""
    resultado = {"usuarios_processados": 0, "enfileiradas": 0}
    cursor = db.configuracoes.find({"tipo": "regua_cobranca", "dados.ativo": True})
    async for doc in cursor:
        uid = doc.get("usuario_id")
        if not uid:
            continue
        stats = await processar_regua(uid)
        resultado["usuarios_processados"] += 1
        resultado["enfileiradas"] += stats.get("enfileiradas", 0)
    return resultado

"""
Job: Resumo semanal via WhatsApp para o gestor.

Toda segunda-feira envia, para cada gestor com WhatsApp conectado, um resumo
da carteira: juros em aberto (empréstimos abertos), parcelas vencidas e a vencer
nos próximos 7 dias — para o gestor cobrar mais rápido.

Envia para o próprio número conectado do gestor (whatsapp_conexoes.numero_telefone)
via Evolution API (services/whatsapp_service.enviar_mensagem_whatsapp).

Uso manual:
    python -m jobs.resumo_whatsapp_job
"""
from datetime import datetime, timezone, timedelta

from config import db
from services.whatsapp_service import enviar_mensagem_whatsapp

STATUS_ABERTO = ["pendente", "parcial", "atrasado"]


def _brl(valor: float) -> str:
    s = f"{valor:,.2f}"
    # Converter para pt-BR: 1,234.56 -> 1.234,56
    return "R$ " + s.replace(",", "X").replace(".", ",").replace("X", ".")


def _parse(value):
    if not value:
        return None
    if isinstance(value, datetime):
        return value if value.tzinfo else value.replace(tzinfo=timezone.utc)
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except (ValueError, TypeError):
        return None


async def _resumo_do_gestor(usuario_id: str) -> dict:
    """Calcula o resumo da carteira de um gestor."""
    hoje = datetime.now(timezone.utc)
    limite_7d = hoje + timedelta(days=7)

    emprestimos = await db.emprestimos.find(
        {"usuario_id": usuario_id, "status": {"$in": ["ativo", "inadimplente"]},
         "deleted": {"$ne": True}},
        {"_id": 0, "id": 1, "sem_prazo": 1}
    ).to_list(100000)

    ids = [e["id"] for e in emprestimos]
    ids_abertos = {e["id"] for e in emprestimos if e.get("sem_prazo")}
    if not ids:
        return {
            "emprestimos_ativos": 0, "vencidas_qtd": 0, "vencidas_total": 0.0,
            "a_vencer_qtd": 0, "a_vencer_total": 0.0, "juros_aberto_total": 0.0,
        }

    parcelas = await db.parcelas.find(
        {"emprestimo_id": {"$in": ids}, "deleted": {"$ne": True},
         "status": {"$in": STATUS_ABERTO}},
        {"_id": 0, "emprestimo_id": 1, "data_vencimento": 1, "valor_total": 1,
         "valor_pago": 1, "valor_multa": 1, "valor_juros_mora": 1}
    ).to_list(500000)

    vencidas_qtd = 0
    vencidas_total = 0.0
    a_vencer_qtd = 0
    a_vencer_total = 0.0
    juros_aberto_total = 0.0

    for p in parcelas:
        saldo = (
            (p.get("valor_total", 0) or 0)
            + (p.get("valor_multa", 0) or 0)
            + (p.get("valor_juros_mora", 0) or 0)
            - (p.get("valor_pago", 0) or 0)
        )
        if saldo <= 0.005:
            continue
        venc = _parse(p.get("data_vencimento"))
        if p.get("emprestimo_id") in ids_abertos:
            juros_aberto_total += saldo
        if venc and venc < hoje:
            vencidas_qtd += 1
            vencidas_total += saldo
        elif venc and hoje <= venc <= limite_7d:
            a_vencer_qtd += 1
            a_vencer_total += saldo

    return {
        "emprestimos_ativos": len(emprestimos),
        "vencidas_qtd": vencidas_qtd,
        "vencidas_total": round(vencidas_total, 2),
        "a_vencer_qtd": a_vencer_qtd,
        "a_vencer_total": round(a_vencer_total, 2),
        "juros_aberto_total": round(juros_aberto_total, 2),
    }


def _montar_mensagem(nome: str, r: dict) -> str:
    hoje_str = datetime.now(timezone.utc).strftime("%d/%m/%Y")
    linhas = [
        f"📊 *Resumo semanal — Kredor* ({hoje_str})",
        f"Olá, {nome}! Aqui está o panorama da sua carteira:",
        "",
        f"📁 Empréstimos ativos: *{r['emprestimos_ativos']}*",
        f"💰 Juros em aberto (empréstimos abertos): *{_brl(r['juros_aberto_total'])}*",
        f"🔴 Parcelas vencidas: *{r['vencidas_qtd']}* — {_brl(r['vencidas_total'])}",
        f"🟡 A vencer nos próximos 7 dias: *{r['a_vencer_qtd']}* — {_brl(r['a_vencer_total'])}",
    ]
    if r["vencidas_qtd"] > 0:
        linhas.append("")
        linhas.append("👉 Priorize a cobrança das parcelas vencidas para não acumular semanas.")
    return "\n".join(linhas)


async def enviar_resumo_semanal_whatsapp() -> dict:
    """Envia o resumo semanal para todos os gestores com WhatsApp conectado."""
    conexoes = await db.whatsapp_conexoes.find(
        {"status": "conectado", "deleted": {"$ne": True}}, {"_id": 0}
    ).to_list(10000)

    enviados = 0
    falhas = 0
    sem_numero = 0

    for conx in conexoes:
        usuario_id = conx.get("usuario_id")
        numero = conx.get("numero_telefone")
        if not usuario_id or not numero:
            sem_numero += 1
            continue

        usuario = await db.usuarios.find_one({"id": usuario_id}, {"_id": 0, "nome": 1})
        nome = (usuario or {}).get("nome", "gestor")

        resumo = await _resumo_do_gestor(usuario_id)
        mensagem = _montar_mensagem(nome, resumo)

        try:
            res = await enviar_mensagem_whatsapp(usuario_id, numero, mensagem)
            if res.get("success"):
                enviados += 1
            else:
                falhas += 1
                print(f"⚠️ Falha ao enviar resumo p/ {usuario_id}: {res.get('message')}")
        except Exception as e:
            falhas += 1
            print(f"❌ Erro ao enviar resumo p/ {usuario_id}: {e}")

    resultado = {
        "conexoes": len(conexoes),
        "enviados": enviados,
        "falhas": falhas,
        "sem_numero": sem_numero,
    }

    try:
        await db.jobs_execucoes.insert_one({
            "job": "resumo_semanal_whatsapp",
            "executado_em": datetime.now(timezone.utc).isoformat(),
            "resultado": resultado,
        })
    except Exception:
        pass

    return resultado


async def job_resumo_semanal_whatsapp():
    print(f"⏰ [Job] Resumo semanal WhatsApp - {datetime.now(timezone.utc).isoformat()}")
    resultado = await enviar_resumo_semanal_whatsapp()
    print(f"✅ Resumo semanal WhatsApp: {resultado}")
    return resultado


if __name__ == "__main__":
    import asyncio
    print(asyncio.run(job_resumo_semanal_whatsapp()))

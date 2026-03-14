"""
Job para processar fila de mensagens WhatsApp
Executa periodicamente para enviar mensagens que estão na fila
"""
from datetime import datetime, timezone
from config import db
from services.whatsapp_fila_service import WhatsAppFilaService


async def job_processar_fila_whatsapp():
    """
    Processa fila de mensagens WhatsApp de todos os usuários
    Executa a cada 2 minutos
    """
    try:
        fila_service = WhatsAppFilaService(db)

        # Buscar usuarios que tem mensagens pendentes na fila
        usuarios_com_fila = await db.whatsapp_fila.distinct(
            "usuario_id",
            {"status": {"$in": ["pendente", "aguardando_retry"]}}
        )

        if not usuarios_com_fila:
            return {"success": True, "mensagem": "Fila vazia", "processadas": 0}

        total_sucesso = 0
        total_erro = 0
        total_aguardando = 0

        for usuario_id in usuarios_com_fila:
            try:
                stats = await fila_service.processar_fila(usuario_id, limite=10)
                total_sucesso += stats.get("sucesso", 0)
                total_erro += stats.get("erro", 0)
                total_aguardando += stats.get("aguardando", 0)
            except Exception as e:
                print(f"   Erro ao processar fila do usuario {usuario_id}: {e}")

        if total_sucesso > 0 or total_erro > 0:
            print(f"[WhatsApp Fila] Processadas: {total_sucesso} enviadas, {total_erro} erros, {total_aguardando} aguardando")

        # Limpar mensagens antigas processadas (mais de 7 dias)
        await fila_service.limpar_fila_antiga(dias=7)

        return {
            "success": True,
            "sucesso": total_sucesso,
            "erro": total_erro,
            "aguardando": total_aguardando
        }

    except Exception as e:
        print(f"[WhatsApp Fila] Erro no job: {e}")
        return {"success": False, "error": str(e)}

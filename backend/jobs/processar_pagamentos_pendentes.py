"""
Job automático para processar pagamentos pendentes (DESATIVADO)

Este job foi desativado pois o sistema agora usa apenas Asaas + Mercado Pago
que possuem webhooks automáticos. Stripe foi removido do sistema.
"""
from services.logging_service import get_logger
logger = get_logger("gestorcred.processar_pagamentos_pendentes")

import asyncio
from datetime import datetime


async def processar_pagamentos_pendentes():
    """
    Job desativado - Sistema agora usa webhooks automáticos do Asaas e Mercado Pago
    
    Returns:
        dict: Status do job (sempre desativado)
    """
    logger.info("ℹ️ Job de pagamentos pendentes desativado (Stripe removido)")
    logger.info("   Sistema usa webhooks automáticos: Asaas + Mercado Pago")
    return {
        "processados": 0,
        "message": "Job desativado - Stripe removido",
        "timestamp": datetime.now().isoformat()
    }


if __name__ == "__main__":
    asyncio.run(processar_pagamentos_pendentes())

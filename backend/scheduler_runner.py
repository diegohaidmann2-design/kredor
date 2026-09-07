"""
Runner dedicado do scheduler de jobs (APScheduler).

Roda como serviço próprio (container `gestorcred_scheduler`), isolado dos
workers da API. Assim os jobs executam em UMA única instância: os workers
gunicorn sobem com RUN_SCHEDULER=false e não instanciam scheduler nenhum,
eliminando a execução duplicada (antes: 1 scheduler por worker => cada job 2x).

Uso local:
    python -m scheduler_runner
"""
import asyncio
import logging
import os
import signal
from pathlib import Path

from scheduler import setup_scheduler, shutdown_scheduler

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger("gestorcred.scheduler_runner")

HEARTBEAT_FILE = Path(os.environ.get("SCHEDULER_HEARTBEAT_FILE", "/tmp/scheduler_heartbeat"))
HEARTBEAT_INTERVAL_S = 30


async def _heartbeat_loop(stop: asyncio.Event) -> None:
    """Toca o arquivo de heartbeat; o healthcheck do container usa o mtime
    para detectar event loop travado."""
    while not stop.is_set():
        try:
            HEARTBEAT_FILE.touch()
        except OSError as e:
            logger.warning("Falha ao escrever heartbeat: %s", e)
        try:
            await asyncio.wait_for(stop.wait(), timeout=HEARTBEAT_INTERVAL_S)
        except asyncio.TimeoutError:
            pass


async def main() -> None:
    setup_scheduler()
    logger.info("Scheduler runner no ar - instancia unica dos jobs automaticos")

    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, stop.set)

    hb = asyncio.create_task(_heartbeat_loop(stop))
    await stop.wait()

    logger.info("Sinal de parada recebido - encerrando scheduler...")
    hb.cancel()
    shutdown_scheduler()


if __name__ == "__main__":
    asyncio.run(main())

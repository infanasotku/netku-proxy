import asyncio
from logging import Logger
from contextlib import asynccontextmanager

from dependency_injector.wiring import inject, Provide

from app.services.outbox import OutboxService
from app.container import Container


@asynccontextmanager
@inject
async def start_outbox_relay(
    logger: Logger, outbox_service: OutboxService = Provide[Container.engine_service]
):
    async def _loop():
        await outbox_service.run_forever()

    async def _wrap():
        try:
            await _loop()
        except Exception:
            logger.critical("Unhandled error occured in ourbox relay:", exc_info=True)

    task = asyncio.create_task(_wrap())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task  # Forward erros from task
        except asyncio.CancelledError:
            pass

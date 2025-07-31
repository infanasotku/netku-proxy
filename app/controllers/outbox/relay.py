import asyncio
from logging import Logger
from contextlib import asynccontextmanager
from typing import Awaitable, cast

from dependency_injector.wiring import inject, Provide

from app.container import Container
from app.services.outbox import OutboxService


@asynccontextmanager
@inject
async def start_outbox_relay(logger: Logger, container: Container = Provide[Container]):
    async def _loop():
        outbox_service = await cast(
            Awaitable[OutboxService], container.outbox_service()
        )
        while True:
            result = await outbox_service.process_batch()
            for r in result:
                if not r.success:
                    logger.error(
                        f"Outbox message with ID {r.id} failed to process, attempts: {r.attempts}, reason: {r.error}."
                    )
            await asyncio.sleep(200 / 1000)

    async def _wrap():
        try:
            await _loop()
        except Exception:
            logger.critical("Unhandled error occured in outbox relay:", exc_info=True)

    task = asyncio.create_task(_wrap())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task  # Forward erros from task
        except asyncio.CancelledError:
            pass

import asyncio
from logging import Logger
from contextlib import asynccontextmanager

from dependency_injector.wiring import inject, Provide
from sentry_sdk import start_transaction

from app.container import Container


@asynccontextmanager
@inject
async def start_outbox_relay(logger: Logger, container: Container = Provide[Container]):
    async def _loop():
        outbox_service = await container.outbox_service()
        while True:
            with start_transaction(
                op="worker", name="WORK /outbox/process-batch"
            ) as tx:
                result = await outbox_service.process_batch()
                if len(result) == 0:
                    tx.set_tag("empty_batch", "1")

                for r in result:
                    if not r.success:
                        logger.error(
                            f"Outbox message with ID {r.record.id} failed to process, attempts: {r.attempts}, reason: {r.error}."
                        )
            await asyncio.sleep(1.5)

    async def _wrap():
        try:
            await _loop()
        except Exception:
            logger.critical("Unhandled error occurred in outbox relay:", exc_info=True)

    task = asyncio.create_task(_wrap())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task  # Forward errors from task
        except asyncio.CancelledError:
            pass

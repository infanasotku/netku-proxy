import asyncio
from logging import Logger
from contextlib import asynccontextmanager


@asynccontextmanager
async def start_outbox_relay(logger: Logger):
    async def _loop():
        pass

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

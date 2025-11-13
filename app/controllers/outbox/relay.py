import asyncio
import traceback
from contextlib import AsyncExitStack, asynccontextmanager

from dependency_injector.wiring import Provide, inject
from sentry_sdk import start_transaction

from app.container import Container
from app.services.outbox import OutboxService


@inject
async def _get_container(container: Container = Provide[Container]):
    return container


def _relay(func):
    @asynccontextmanager
    async def _outer():
        container = await _get_container()
        logger = container.logger()

        async def _wrap():
            try:
                await func()
            except Exception:
                logger.critical(
                    f"Unhandled error occurred in outbox relay: {traceback.format_exc()}",
                )

        task = asyncio.create_task(_wrap())

        try:
            yield
        finally:
            task.cancel()

            try:
                await task  # Forward errors from task
            except asyncio.CancelledError:
                pass

    return _outer


@_relay
@inject
async def _handle_outbox_batch(svc: OutboxService = Provide[Container.outbox_service]):
    while True:
        with start_transaction(
            op="worker", name="WORK /outbox/process-outbox-batch"
        ) as tx:
            result = await svc.process_outbox_batch()
            if result == 0:
                tx.set_tag("empty_batch", "1")

        await asyncio.sleep(200 / 1000)


@_relay
@inject
async def _handle_delivery_tasks_batch(
    svc: OutboxService = Provide[Container.outbox_service],
):
    while True:
        with start_transaction(
            op="worker", name="WORK /outbox/process-delivery-tasks-batch"
        ) as tx:
            result = await svc.process_engine_delivery_tasks()
            if result == 0:
                tx.set_tag("empty_batch", "1")

        await asyncio.sleep(200 / 1000)


@asynccontextmanager
async def start_outbox_relay():
    async with AsyncExitStack() as stack:
        await stack.enter_async_context(_handle_outbox_batch())
        await stack.enter_async_context(_handle_delivery_tasks_batch())
        yield

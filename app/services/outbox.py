import asyncio

from app.infra.database.uow import PostgresOutboxUnitOfWork
from app.infra.rabbit.publisher import RabbitPublisher


class OutboxService:
    def __init__(
        self,
        uow: PostgresOutboxUnitOfWork,
        publisher: RabbitPublisher,
        *,
        idle_ms=200,
        batch=200,
    ) -> None:
        self._uow = uow
        self._publisher = publisher
        self._idle_ms = idle_ms
        self._batch = batch

    async def _process_batch(self) -> None:
        async with self._uow.begin() as uow:
            events = await uow.outbox.claim_batch(self._batch)
            if not events:
                return

            for event in events:
                try:
                    await self._publisher.publish(event)
                except Exception as e:
                    # Handle publishing error (e.g., log it)
                    pass

    async def run_forever(self) -> None:
        while True:
            await self._process_batch()
            await asyncio.sleep(self._idle_ms / 1000)

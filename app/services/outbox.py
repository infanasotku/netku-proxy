import asyncio

from app.infra.database.uow import PostgresOutboxUnitOfWork


class OutboxService:
    def __init__(
        self, uow: PostgresOutboxUnitOfWork, *, idle_ms=200, batch=200
    ) -> None:
        self._uow = uow
        self._idle_ms = idle_ms
        self._batch = batch

    async def _process_batch(self) -> None:
        async with self._uow.begin() as uow:
            pass

    async def run_forever(self) -> None:
        while True:
            await self._process_batch()
            await asyncio.sleep(self._idle_ms / 1000)

from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.contracts.uow import EngineUnitOfWork
from app.domains.event import DomainEvent
from app.infra.database.repositories.engine import PostgresEngineRepository
from app.infra.database.repositories.outbox import PostgresOutboxRepository


class PostgresEngineUnitOfWork(EngineUnitOfWork):
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._session_factory = session_factory
        self._events: list[DomainEvent] = []
        self._caused_by: str | None = None

    async def _start(self, caused_by=None):
        self._caused_by = caused_by
        self._session = self._session_factory()
        self._transaction = await self._session.begin()

        self._engine = PostgresEngineRepository(self._session)
        self._outbox = PostgresOutboxRepository(self._session)

    async def _finish(self, exc: Exception | None):
        try:
            if exc is None:
                await self._flush_outbox()

                await self._transaction.commit()
            else:
                await self._transaction.rollback()
        except Exception:
            await self._transaction.rollback()
            raise
        finally:
            await self._session.close()

    async def _flush_outbox(self):
        if len(self._events) == 0:
            return
        await self._outbox.store(self._events, caused_by=self._caused_by)
        self._events.clear()

    @asynccontextmanager
    async def begin(self, *, caused_by=None):
        await self._start(caused_by)
        try:
            yield self
        except Exception as e:
            await self._finish(e)
            raise
        else:
            await self._finish(None)

    def collect(self, events):
        self._events.extend(events)

    @property
    def engines(self):
        return self._engine

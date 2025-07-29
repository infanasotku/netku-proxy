from collections.abc import Iterable
from contextlib import asynccontextmanager
from typing import Any, Protocol, AsyncContextManager

from sqlalchemy.ext.asyncio import async_sessionmaker, AsyncSession

from app.domains.event import DomainEvent
from app.infra.database.repositories.engine import PostgresEngineRepository
from app.infra.database.repositories.outbox import PostgresOutboxRepository


class TransactionBoundary(Protocol):
    """
    **Transaction Boundary** protocol.

    Defines the minimal API to demarcate a database transaction.

    Responsibilities
    ----------------
    - Provide `begin()` yielding an async context manager that encloses a *single* database transaction.
    - Ensure that all work inside the context either **commits** or **rolls back** together.
    - Accept an optional `caused_by` correlation key so callers can pass idempotency context (e.g. inbound message id) — the implementation may propagate it to outbox/internals to keep keys stable.

    Notes
    -----
    - Keep transactions short — do not perform network I/O while the transaction is open.
    - This protocol does **not** prescribe event buffering; that is the role of `DomainEventsBuffer`.
    """

    def begin(self, *, caused_by: str | None = None) -> AsyncContextManager[Any]: ...


class DomainEventsBuffer(Protocol):
    """
    **Domain Events Buffer** protocol.

    A tiny interface for collecting `DomainEvent` instances during a use-case.
    Implementations persist the collected events into the **outbox** table *right before commit* of the surrounding transaction (Transactional Outbox).

    Responsibilities
    ----------------
    - Provide `collect(events)` to enqueue one or more events.
    - De-duplicate identical events within the same UoW instance (recommended).

    Notes
    -----
    - This protocol does **not** start or commit transactions — pair it with `TransactionBoundary` in concrete UoW implementations.
    """

    def collect(self, events: Iterable[DomainEvent]) -> None:
        """Enqueue domain events to be written to the outbox atomically with state changes."""


class PostgresEngineUnitOfWork(TransactionBoundary, DomainEventsBuffer):
    """
    PostgreSQL implementation of a Unit of Work that combines:

    - `TransactionBoundary` — opens/closes an async SQLAlchemy transaction; and
    - `DomainEventsBuffer` — buffers domain events and flushes them to the outbox just before commit.

    Also supports idempotency by accepting `caused_by` in `begin()` and passing it to the outbox repository.
    """

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


class PostgresOutboxUnitOfWork(TransactionBoundary):
    """
    Thin transactional boundary used by the outbox replayer/publisher.

    It implements only `TransactionBoundary` — no domain-event buffering.
    """

    def __init__(self, session_factory: async_sessionmaker[AsyncSession]) -> None:
        super().__init__()
        self._session_factory = session_factory

    @property
    def outbox(self):
        return self._outbox

    @asynccontextmanager
    async def begin(self, *, caused_by: str | None = None):
        session = self._session_factory()
        try:
            async with session.begin():
                self._outbox = PostgresOutboxRepository(session)
                yield self
        finally:
            await session.close()

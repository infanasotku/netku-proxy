from abc import ABC, abstractmethod
from collections.abc import Iterable
from typing import Self, AsyncContextManager


from app.contracts.repositories.engine import EngineRepository
from app.domains.event import DomainEvent


class BaseUnitOfWork(ABC):
    """
    **Unit-of-Work** contract.

    A Unit of Work (UoW) *encapsulates* a transactional boundary:
    everything executed **inside** its context block must either persist
    together (`COMMIT`) or not at all (`ROLLBACK`). Adapters are expected
    to implement this protocol for any persistence technology
    (PostgreSQL, Mongo, Redis-lua, etc.).

    Responsibilities
    ----------------
    1. **Collect Domain Events**
       Provide `collect` so that application services can enqueue
       `DomainEvent` objects during the use-case.
       The concrete adapter must persist them *atomically* with domain
       state (Transactional Outbox pattern).

    2. **Idempotency support**
       Accept an optional *correlation key (caused_by)* in `begin` method (e.g. inbound *stream_id*)
       so that repeated deliveries generate the **same** outbox primary
       key and are safely ignored on conflict.
    """

    @abstractmethod
    def begin(self, *, caused_by: str | None = None) -> AsyncContextManager[Self]: ...

    @abstractmethod
    def collect(self, events: Iterable[DomainEvent]) -> None:
        """
        Buffer a list of `DomainEvent` objects so they can be written
        to the **outbox** table *inside the same database transaction* just
        before commit. Implementations should de-duplicate identical
        objects inside a single UoW instance.
        """


class EngineUnitOfWork(BaseUnitOfWork):
    @property
    @abstractmethod
    def engines(self) -> EngineRepository: ...

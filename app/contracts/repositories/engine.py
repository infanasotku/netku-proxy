from abc import ABC, abstractmethod
from uuid import UUID

from app.domains.engine import Engine


class EngineRepository(ABC):
    @abstractmethod
    async def get(self, engine_id: UUID) -> Engine | None:
        """
        Retrieve the current persistent snapshot of an `Engine` aggregate.

        Unlike `get_for_update`, this method does **not** reserve the aggregate
        for exclusive write access. It is intended for read-only operations and does
        not participate in locking or transactional isolation.
        """

    @abstractmethod
    async def get_for_update(self, engine_id: UUID) -> Engine | None:
        """
        Retrieve the **current persistent snapshot** of an `Engine` aggregate
        and **reserve it for exclusive write-access** for the remainder of the
        caller’s transactional context.
        """

    @abstractmethod
    async def save(self, engine: Engine) -> bool:
        """
        Persist the *current* state of an ``Engine`` aggregate.

        The method **MUST implement an idempotent *upsert***
        semantics:

        * **Insert** – if the aggregate does not exist yet.
        * **Update** – if the stored *version* is *older* than
          `engine.version`.
          "Older" is defined by the concrete adapter, but **MUST** be a strict,
          monotonic ordering (e.g. Redis‐stream `(ver_ts, ver_seq)` or a
          numeric version counter).
        * **No-op** – if the aggregate is already stored with the *same* or a
          *newer* version.  In this case the method must **leave the row
          untouched** and return *False*.

        Returns:
            bool: `True` if INSERT or UPDATE actually changed the persistent
            representation `False` ohterwise.
        """

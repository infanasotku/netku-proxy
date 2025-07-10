from abc import abstractmethod, ABC
from uuid import UUID

from app.domains.engine import Version
from app.schemas.engine import EngineCmd


class EngineRemoveError(KeyError):
    def __init__(self, id: UUID, message: str | None = None) -> None:
        if message is None:
            message = f"Engine with ID {id} does not exist."
        super().__init__(message)
        self.id = id

    def __str__(self) -> str:
        return str(self.args[0])


class EngineService(ABC):
    """
    High-level **use-case interface** responsible for command–side operations on
    the *Engine* aggregate.

    Concrete implementations (e.g., `EngineServiceImpl`) must:

    - open a transactional **Unit of Work**;
    - apply domain rules (`Engine.remove`, `.update`, ...);
    - persist changes through repository ports (`uow.engines.save`);
    - push domain events to the outbox via `uow.collect`.

    The interface itself remains storage-agnostic and side-effect-free, so it
    can be used both in HTTP controllers and stream consumers.
    """

    @abstractmethod
    async def remove(self, id: UUID, *, caused_by: str | None = None, version: Version):
        """
        Idempotently **mark an engine as deleted** (tombstone).

        Behaviour
        ----------
        - **First call** (aggregate exists **and** `version` is newer)
          -> state is updated, domain event `EngineRemoved` is collected.
        - **Subsequent retries** with the *same* `version`
          -> *no‐op* (method exits silently, no new outbox entry).
        - **Aggregate not found**
          -> raises `EngineRemoveError`.

        Args:
            id:
                Primary key of the engine aggregate to be removed.
            caused_by:
                Correlation identifier of the incoming message
                (e.g. Redis *stream_id*).  Propagated into the outbox so that
                duplicate deliveries write the **same** `message_id`.
            version:
                Monotonically increasing value derived from the same `stream_id`
                - used for optimistic concurrency.

        Raises:
            EngineRemoveError:
                If the engine with the given *id* is not present **before**
                executing the command.
        """

    @abstractmethod
    async def upsert(
        self, engine: EngineCmd, *, caused_by: str | None = None, version: Version
    ):
        """
        Create **or** update the engine metadata in an *exactly-once* fashion.

        Decision matrix
        ---------------
        Aggregate state -> Action
        - **Not present** -> *Insert* a new `Engine`
        - **Present `version` newer** -> *Update* existing aggregate
        - **Present `version` older** -> *No-op* – stale duplicate is ignored

        Args:
            engine:
                Validated DTO carrying the desired state
                (`id`, `uuid`, `running`, `addr`, `created`, …).
            caused_by:
                Same correlation key that will become `outbox.id`
                / AMQP `message_id`.  Ensures de-duplication on relay / consumer.
            version:
                Version token guaranteeing proper ordering inside the aggregate.
        """

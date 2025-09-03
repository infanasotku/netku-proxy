from uuid import UUID

from app.infra.grpc.engine import GRPCEngineManager
from app.schemas.engine import EngineCmd
from app.services.exceptions.engine import EngineDeadError, EngineNotExistError

from app.infra.database.uow import PostgresEngineUnitOfWork

from app.domains.engine import Engine, EngineStatus


class EngineService:
    """
    Application‑level service that executes command‑side operations on
    the *Engine* aggregate.

    Responsibilities
    ----------------
    - Open a transactional `~app.infra.database.uow.PostgresEngineUnitOfWork`.
    - Apply domain rules (`Engine.remove`, `Engine.update`, ...).
    - Persist changes via repository ports (`uow.engines.save`).
    - Collect domain events into the outbox with `uow.collect`.
    """

    def __init__(self, uow: PostgresEngineUnitOfWork, manager: GRPCEngineManager):
        self._uow = uow
        self._manager = manager

    async def remove(self, id, *, caused_by=None, version):
        """
        Idempotently **mark an engine as deleted** (tombstone).

        Behaviour
        ---------
        - **First call** when the aggregate exists and `version` is newer -> state updated and `EngineRemoved` event collected.
        - **Subsequent retries** with the *same* `version` -> *no‑op*.
        - **Aggregate not found** -> raises `~app.services.exceptions.engine.EngineNotExistError`.

        Parameters
        ----------
        id : UUID
            Identifier of the engine to remove.
        caused_by : str | None
            Correlation identifier propagated into the outbox.
        version : ~app.domains.engine.Version
            Optimistic concurrency token guaranteeing proper ordering.

        Raises
        ------
        EngineNotExistError
            If the engine does not exist.
        """
        async with self._uow.begin(caused_by=caused_by) as uow:
            current_engine = await uow.engines.get_for_update(id)
            if current_engine is None:
                raise EngineNotExistError(id)
            current_engine.remove(version)

            changed = await uow.engines.save(current_engine)
            if changed:
                uow.collect(current_engine.pull_events())

    async def upsert(self, engine: EngineCmd, *, caused_by=None, version):
        """
        Create **or** update an engine aggregate in an *exactly‑once* fashion.

        Decision matrix
        ---------------
        Aggregate state -> Action
        - **Not present** -> *Insert* new `Engine`.
        - **Present & `version` newer** -> *Update* existing aggregate.
        - **Present & `version` older** -> *No‑op* (stale duplicate).

        Parameters
        ----------
        engine : ~app.schemas.engine.EngineCmd
            Desired state payload.
        caused_by : str | None
            Correlation identifier that becomes `outbox.id` / AMQP `message_id`.
        version : ~app.domains.engine.Version
            Version token guaranteeing proper ordering inside the aggregate.
        """
        async with self._uow.begin(caused_by=caused_by) as uow:
            current_engine = await uow.engines.get_for_update(engine.id)
            if current_engine is None:
                current_engine = Engine(
                    id=engine.id,
                    uuid=engine.uuid,
                    status=EngineStatus.READY,
                    created=engine.created,
                    addr=engine.addr,
                    version=version,
                )
            elif current_engine.status == EngineStatus.DEAD:
                current_engine.restore(engine.running, engine.uuid, version=version)
            else:
                current_engine.update(engine.running, engine.uuid, version=version)

            changed = await uow.engines.save(current_engine)
            if changed:
                uow.collect(current_engine.pull_events())

    async def restart(self, id: UUID, *, uuid: UUID):
        """
        Restart the physics engine **instance**.

        This operation does **not** change persistent state; it delegates to
        `~app.contracts.clients.engine.EngineManager` to perform the actual restart.

        Parameters
        ----------
        id : UUID
            Identifier of the engine aggregate.
        uuid : UUID
            Identifier with which the engine will be restarted.

        Raises
        ------
        EngineNotExistError
            If the engine does not exist.
        EngineDeadError
            If the engine is marked DEAD.
        """
        async with self._uow.begin() as uow:
            engine = await uow.engines.get(id)
            if engine is None:
                raise EngineNotExistError(id)
            if engine.status == EngineStatus.DEAD:
                raise EngineDeadError(id)

            await self._manager.restart(uuid, addr=engine.addr)

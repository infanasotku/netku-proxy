from logging import Logger
from uuid import UUID

from app.domains.engine import Engine, EngineStatus, Version
from app.infra.database.uow import PgEngineUnitOfWorkContext, PgUnitOfWork
from app.infra.grpc.engine import GRPCEngineManager
from app.schemas.engine import EngineCmd
from app.services.exceptions.engine import EngineDeadError, EngineNotExistError


def _is_not_newer_msg(id: UUID):
    return f"Version of engine with ID [{id}] is not newer; no action taken."


class EngineService:
    def __init__(
        self,
        uow: PgUnitOfWork[PgEngineUnitOfWorkContext],
        manager: GRPCEngineManager,
        *,
        logger: Logger,
    ):
        self._uow = uow
        self._manager = manager
        self._logger = logger

    async def mark_dead(self, id, *, caused_by: str, version: Version):
        """
        Idempotently **mark an engine as dead**.

        Behaviour:
        - **First call** when the aggregate exists and `version` is newer -> state updated and `EngineRemoved` event stored.
        - **Subsequent retries** with the *same* `version` -> *no‑op*.
        - **Aggregate not found** -> raises `EngineNotExistError`.

        Arguments:
            caused_by: Correlation identifier propagated into the outbox.
            version: Optimistic concurrency token guaranteeing proper ordering.

        Raises:
            EngineNotExistError
                If the engine does not exist.
        """
        async with self._uow.begin() as uow:
            current_engine = await uow.engines.get_for_update(id)
            self._logger.info(f"Marking engine with ID [{id}] as dead...")
            if current_engine is None:
                raise EngineNotExistError(id)
            current_engine.mark_dead(version)

            changed = await uow.engines.save(current_engine)
            if changed:
                await uow.outbox.store(
                    current_engine.pull_events(), caused_by=caused_by
                )

        if changed:
            self._logger.info(f"Engine with ID [{id}] marked as dead.")
        else:
            self._logger.info(_is_not_newer_msg(id))

    async def upsert(self, engine: EngineCmd, *, caused_by: str, version: Version):
        """
        Create **or** update an engine aggregate in an *exactly‑once* fashion.

        Decision matrix (Aggregate state -> Action):
        - **Not present** -> *Insert* new `Engine` and store event.
        - **Present & `version` newer** -> *Update* existing aggregate and store event.
        - **Present & `version` older** -> *No‑op* (stale duplicate).

        Arguments
            caused_by: Correlation identifier propagated into the outbox.
            version: Optimistic concurrency token guaranteeing proper ordering.
        """
        async with self._uow.begin() as uow:
            current_engine = await uow.engines.get_for_update(engine.id)
            if current_engine is None:
                self._logger.info(f"Creating new engine with ID [{engine.id}]...")
                current_engine = Engine(
                    id=engine.id,
                    uuid=engine.uuid,
                    status=EngineStatus.READY,
                    created=engine.created,
                    addr=engine.addr,
                    version=version,
                )
            elif current_engine.status == EngineStatus.DEAD:
                self._logger.info(f"Restoring dead engine with ID [{engine.id}]...")
                current_engine.restore(engine.running, engine.uuid, version=version)
            else:
                self._logger.info(f"Updating engine with ID [{engine.id}]...")
                current_engine.update(engine.running, engine.uuid, version=version)

            changed = await uow.engines.save(current_engine)
            if changed:
                await uow.outbox.store(
                    current_engine.pull_events(), caused_by=caused_by
                )
        if changed:
            self._logger.info(f"Engine with ID [{engine.id}] upserted.")
        else:
            self._logger.info(_is_not_newer_msg(engine.id))

    async def restart(self, id: UUID, *, uuid: UUID):
        """
        Restart the physics engine **instance**.

        This operation does **not** change persistent state; it delegates to
        `EngineManager` to perform the actual restart.

        Arguments:
            uuid: Identifier with which the engine will be restarted.

        Raises:
            EngineNotExistError
                If the engine does not exist.
            EngineDeadError
                If the engine is marked DEAD.
        """
        async with self._uow.begin() as uow:
            engine = await uow.engines.get(id)
            self._logger.info(f"Restarting engine with ID [{id}]...")
            if engine is None:
                raise EngineNotExistError(id)
            if engine.status == EngineStatus.DEAD:
                raise EngineDeadError(id)

        await self._manager.restart(uuid, addr=engine.addr)
        self._logger.info(f"Engine with ID [{id}] restarted.")

    async def remove_dead_engines(self):
        pass

from app.contracts.services.engine import EngineService, EngineRemoveError
from app.contracts.uow import EngineUnitOfWork

from app.domains.engine import Engine, EngineStatus


class EngineServiceImpl(EngineService):
    def __init__(self, uow: EngineUnitOfWork):
        self._uow = uow

    async def remove(self, id, *, caused_by=None, version):
        async with self._uow.begin(caused_by=caused_by) as uow:
            current_engine = await uow.engines.get_for_update(id)
            if current_engine is None:
                raise EngineRemoveError(id)
            current_engine.remove(version)

            changed = await uow.engines.save(current_engine)
            if changed:
                uow.collect(current_engine.pull_events())

    async def upsert(self, engine, *, caused_by=None, version):
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
            else:
                current_engine.update(engine.running, engine.uuid, version=version)

            changed = await uow.engines.save(current_engine)
            if changed:
                uow.collect(current_engine.pull_events())

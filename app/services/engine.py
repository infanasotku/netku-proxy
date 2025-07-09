from app.contracts.services.proxy import EngineService, EngineRemoveError
from app.contracts.uow import EngineUnitOfWork

from app.domains.engine import EngineMeta, EngineStatus


class EngineServiceImpl(EngineService):
    def __init__(self, uow: EngineUnitOfWork):
        self._uow = uow

    async def remove(self, id, *, caused_by=None, version):
        async with self._uow.begin(caused_by=caused_by) as uow:
            current_meta = await uow.engines.get_for_update(id)
            if current_meta is None:
                raise EngineRemoveError(id)
            current_meta.remove(version)

            changed = await uow.engines.save(current_meta)
            if changed:
                uow.collect(current_meta.pull_events())

    async def upsert(self, meta, *, caused_by=None, version):
        async with self._uow.begin(caused_by=caused_by) as uow:
            current_meta = await uow.engines.get_for_update(meta.id)
            if current_meta is None:
                current_meta = EngineMeta(
                    id=meta.id,
                    uuid=meta.uuid,
                    status=EngineStatus.READY,
                    created=meta.created,
                    addr=meta.addr,
                    version=version,
                )
            else:
                current_meta.update(meta.running, meta.uuid, version=version)

            changed = await uow.engines.save(current_meta)
            if changed:
                uow.collect(current_meta.pull_events())

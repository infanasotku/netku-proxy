from uuid import UUID

from app.contracts.repositories.engine import EngineRepository
from app.infra.database.repositories.base import BasePostgresRepository
from app.domains.engine import EngineMeta


class PostgresEngineRepository(EngineRepository, BasePostgresRepository):
    async def get_for_update(self, engine_id: UUID) -> EngineMeta | None:
        raise NotImplementedError

    async def save(self, meta: EngineMeta) -> bool:
        raise NotImplementedError

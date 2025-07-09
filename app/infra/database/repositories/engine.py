from uuid import UUID

from app.contracts.repositories.engine import EngineRepository
from app.infra.database.repositories.base import BasePostgresRepository
from app.domains.engine import Engine


class PostgresEngineRepository(EngineRepository, BasePostgresRepository):
    async def get_for_update(self, engine_id: UUID) -> Engine | None:
        raise NotImplementedError

    async def save(self, meta: Engine) -> bool:
        raise NotImplementedError

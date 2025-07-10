from uuid import UUID

from sqlalchemy import literal_column, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.contracts.repositories.engine import EngineRepository
from app.infra.database.repositories.base import BasePostgresRepository
from app.domains.engine import Engine, Version
from app.infra.database.models import Engine as EngineModel


class PostgresEngineRepository(EngineRepository, BasePostgresRepository):
    async def get_for_update(self, engine_id: UUID) -> Engine | None:
        stmt = select(EngineModel).where(EngineModel.id == engine_id).with_for_update()
        row = await self._session.scalar(stmt)
        if row is None:
            return None

        return Engine(
            id=engine_id,
            uuid=row.uuid,
            status=row.status,
            created=row.created,
            addr=row.addr,
            version=Version(ts=row.version_timestamp, seq=row.version_seq),
        )

    async def save(self, engine) -> bool:
        update_dict = dict(
            uuid=engine.uuid,
            status=engine.status,
            version_timestamp=engine.version.ts,
            version_seq=engine.version.seq,
        )

        stmt = (
            pg_insert(EngineModel)
            .values(
                id=engine.id, created=engine.created, addr=engine.addr, **update_dict
            )
            .on_conflict_do_update(
                index_elements=(EngineModel.id,),
                set_=update_dict,
                where=tuple_(EngineModel.version_timestamp, EngineModel.version_seq)
                <= (engine.version.ts, engine.version.seq),
            )
            .returning(literal_column("TRUE"))
        )

        row: bool | None = await self._session.scalar(stmt)

        return bool(row)

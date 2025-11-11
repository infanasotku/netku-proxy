from uuid import UUID

from sentry_sdk import start_span
from sqlalchemy import delete, literal_column, select, tuple_
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domains.engine import Engine, EngineStatus, Version
from app.infra.database.models import Engine as EngineModel
from app.infra.database.repositories.base import PostgresRepository


class PgEngineRepository(PostgresRepository):
    async def get_for_update(self, engine_id: UUID) -> Engine | None:
        """
        Retrieve the **current persistent snapshot** of an `Engine` aggregate
        and **reserve it for exclusive write-access** for the remainder of the
        caller’s transactional context.
        """
        with start_span(op="db", name="get_engine_for_update") as span:
            span.set_tag("engine_id", str(engine_id))

            stmt = (
                select(EngineModel).where(EngineModel.id == engine_id).with_for_update()
            )
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
            representation `False` otherwise.
        """
        with start_span(op="db", name="save_engine") as span:
            span.set_tag("engine_id", str(engine.id))

            update_dict = dict(
                uuid=engine.uuid,
                status=engine.status,
                version_timestamp=engine.version.ts,
                version_seq=engine.version.seq,
            )

            stmt = (
                pg_insert(EngineModel)
                .values(
                    id=engine.id,
                    created=engine.created,
                    addr=engine.addr,
                    **update_dict,
                )
                .on_conflict_do_update(
                    index_elements=(EngineModel.id,),
                    set_=update_dict,
                    where=tuple_(EngineModel.version_timestamp, EngineModel.version_seq)
                    < (engine.version.ts, engine.version.seq),
                )
                .returning(literal_column("TRUE"))
            )

            row: bool | None = await self._session.scalar(stmt)

            return bool(row)

    async def get(self, engine_id: UUID) -> Engine | None:
        with start_span(op="db", name="get_engine") as span:
            span.set_tag("engine_id", str(engine_id))

            stmt = select(EngineModel).where(EngineModel.id == engine_id)
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

    async def remove_dead(self) -> int:
        with start_span(op="db", name="remove_dead_engines") as span:
            stmt = (
                delete(EngineModel)
                .where(EngineModel.status == EngineStatus.DEAD)
                .returning(1)
            )
            rows = await self._session.scalars(stmt)
            deleted = len(rows.all())

            span.set_tag("deleted_count", deleted)
            return deleted

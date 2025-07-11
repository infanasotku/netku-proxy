from uuid import NAMESPACE_URL, uuid5
import json

from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.contracts.repositories.outbox import OutboxRepository
from app.infra.database.repositories.base import BasePostgresRepository
from app.domains.event import DomainEvent
from app.infra.database.models import OutboxRecord


class PostgresOutboxRepository(OutboxRepository, BasePostgresRepository):
    async def store(
        self, events: list[DomainEvent], *, caused_by: str | None = None
    ) -> None:
        for ev in events:
            if caused_by:
                oid = uuid5(NAMESPACE_URL, f"{caused_by}:{ev.id}")
            else:
                oid = ev.id

            caused_by = caused_by if caused_by is not None else str(oid)

            stmt = (
                pg_insert(OutboxRecord)
                .values(
                    id=oid,
                    caused_by=caused_by,
                    body=json.loads(json.dumps(ev.to_dict(), default=str)),
                )
                .on_conflict_do_nothing(index_elements=["id"])
            )
            await self._session.execute(stmt)

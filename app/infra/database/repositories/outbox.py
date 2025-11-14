import json
from datetime import datetime
from uuid import NAMESPACE_URL, UUID, uuid5

from sentry_sdk import start_span
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domains.event import DomainEvent
from app.infra.database.models import Outbox
from app.infra.database.repositories.base import PostgresRepository
from app.infra.utils.time import now_utc
from app.schemas.outbox import OutboxDTO


class PgOutboxRepository(PostgresRepository):
    async def store(self, events: list[DomainEvent], *, caused_by: str) -> None:
        """
        Persist a **batch** of `DomainEvent` inside the **current transaction.

        Args:
            events:
                A list of domain events collected during the use-case execution.
            caused_by:
                Deduplication key (e.g. Redis ``stream_id`` of the
                upstream message).
        """
        with start_span(op="db", name="store_outbox_events") as span:
            span.set_tag("caused_by", caused_by)
            span.set_tag("events_count", len(events))

            for ev in events:
                oid = uuid5(NAMESPACE_URL, f"{caused_by}:{ev.id}")

                caused_by = caused_by if caused_by is not None else str(oid)

                stmt = (
                    pg_insert(Outbox)
                    .values(
                        id=oid,
                        caused_by=caused_by,
                        body=json.loads(json.dumps(ev.to_dict(), default=str)),
                    )
                    .on_conflict_do_nothing(index_elements=["id"])
                )
                await self._session.execute(stmt)

    async def claim_batch(self, batch: int, *, max_attempts: int) -> list[OutboxDTO]:
        """
        Claim a batch of unprocessed outbox records.

        This method selects up to `batch` unpublished outbox records from the database,
        locking them for update and skipping any that are already locked by other transactions.
        """
        with start_span(op="db", name="claim_outbox_batch") as span:
            stmt = (
                select(Outbox)
                .where(
                    and_(
                        Outbox.fanned_out.is_(False),
                        Outbox.attempts < max_attempts,
                        Outbox.next_attempt_at <= now_utc(),
                    )
                )
                .with_for_update(skip_locked=True)
                .limit(batch)
            )

            rows = await self._session.scalars(stmt)

            result = [
                OutboxDTO(
                    event=DomainEvent.from_dict(row.body),
                    caused_by=row.caused_by,
                    id=row.id,
                    attempts=row.attempts,
                )
                for row in rows
            ]

            span.set_tag("claimed_count", len(result))

            return result

    async def mark_fanned_out(self, outbox_id: UUID) -> None:
        """Updates the `fanned_out` status to True."""
        with start_span(op="db", name="mark_outbox_fanned_out") as span:
            span.set_tag("outbox.id", str(outbox_id))

            stmt = (
                update(Outbox)
                .where(Outbox.id == outbox_id)
                .values(
                    fanned_out=True,
                    fanned_out_at=now_utc(),
                    attempts=Outbox.attempts + 1,
                )
            )
            await self._session.execute(stmt)

    async def mark_failed(self, next_attempt_at: datetime, *, outbox_id: UUID) -> None:
        """
        Marks the specified outbox record as failed.
        Increments the `attempts` counter for the outbox record identified by `outbox_id`.
        """
        with start_span(op="db", name="mark_outbox_failed") as span:
            span.set_tag("outbox.id", str(outbox_id))

            stmt = (
                update(Outbox)
                .where(Outbox.id == outbox_id)
                .values(attempts=Outbox.attempts + 1, next_attempt_at=next_attempt_at)
            )
            await self._session.execute(stmt)

    async def extract_events(self, outbox_ids: list[UUID]) -> list[DomainEvent]:
        """
        Extract events and return them in the order of the original list.
        """
        with start_span(op="db", name="extract_outbox_events"):
            stmt = select(Outbox.id, Outbox.body).where(Outbox.id.in_(outbox_ids))
            rows = (await self._session.execute(stmt)).all()

            id_body_dict = {id: body for id, body in rows}

            events = [DomainEvent.from_dict(id_body_dict[id]) for id in outbox_ids]
            return events

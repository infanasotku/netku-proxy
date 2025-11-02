import json
from datetime import datetime, timezone
from uuid import NAMESPACE_URL, UUID, uuid5

from sentry_sdk import start_span
from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.domains.event import DomainEvent
from app.infra.database.models import Outbox
from app.infra.database.repositories.base import PostgresRepository
from app.schemas.outbox import OutboxDTO


class PgOutboxRepository(PostgresRepository):
    async def store(
        self, events: list[DomainEvent], *, caused_by: str | None = None
    ) -> None:
        """
        Persist a **batch** of `DomainEvent` objects into the *outbox*
        table/collection inside the **current transaction.

        Purpose:
        -------
            Implements the *Transactional Outbox* pattern:
            the events are saved **atomically** with the business data so that a
            single database commit guarantees either *both* are durable or *neither*.

        Args:
            events:
                A list of domain events collected during the use-case execution.
                The adapter must iterate the list **in order** and write each event
                as an individual outbox record.
            caused_by:
                *Optional* deduplication key (e.g. Redis ``stream_id`` of the
                upstream message).
                If provided, **every** stored record should use this value including `event.id` as its
                primary key; otherwise only `event.id` is used.  This enables
                *exactly-once* semantics on repeat deliveries.
        """
        with start_span(op="db", name="Store outbox events") as span:
            span.set_tag("caused_by", caused_by)
            span.set_tag("events_count", len(events))

            for ev in events:
                if caused_by:
                    oid = uuid5(NAMESPACE_URL, f"{caused_by}:{ev.id}")
                else:
                    oid = ev.id

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
        Claims a batch of unpublished outbox records for processing.
        This method selects up to `batch` unpublished outbox records from the database,
        locking them for update and skipping any that are already locked by other transactions.
        It then returns a list of `DomainEvent` instances created from the record bodies.

        Args:
            batch (int): The maximum number of outbox records to claim.
            max_attempts (int): The maximum number of publish attempts for each record.
        """
        with start_span(op="db", name="Claim outbox events") as span:
            stmt = (
                select(Outbox)
                .where(
                    and_(
                        Outbox.fanned_out == False,  # noqa: E712
                        Outbox.attempts < max_attempts,
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

    async def mark_sent(self, outbox_id: UUID) -> None:
        """
        Marks the specified outbox record as sent.
        Updates the `published` status to True, sets the `published_at` timestamp to the current time,
        and increments the `attempts` counter for the outbox record identified by `outbox_id`.
        """
        with start_span(op="db", name="Mark outbox as sent") as span:
            span.set_tag("outbox.id", str(outbox_id))

            stmt = (
                update(Outbox)
                .where(Outbox.id == outbox_id)
                .values(
                    published=True,
                    published_at=datetime.now(timezone.utc),
                    attempts=Outbox.attempts + 1,
                )
            )
            await self._session.execute(stmt)

    async def mark_failed(self, outbox_id: UUID) -> None:
        """
        Marks the specified outbox record as failed.
        Increments the `attempts` counter for the outbox record identified by `outbox_id`.
        """
        with start_span(op="db", name="Mark outbox as failed") as span:
            span.set_tag("outbox.id", str(outbox_id))

            stmt = (
                update(Outbox)
                .where(Outbox.id == outbox_id)
                .values(attempts=Outbox.attempts + 1)
            )
            await self._session.execute(stmt)

from uuid import NAMESPACE_URL, uuid5
import json

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy import select

from app.infra.database.repositories.base import PostgresRepository
from app.domains.event import DomainEvent
from app.infra.database.models import OutboxRecord


class PostgresOutboxRepository(PostgresRepository):
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

    async def claim_batch(self, batch: int) -> list[DomainEvent]:
        """
        Claims a batch of unpublished outbox records for processing.
        This method selects up to `batch` unpublished outbox records from the database,
        locking them for update and skipping any that are already locked by other transactions.
        It then returns a list of `DomainEvent` instances created from the record bodies.

        Args:
            batch (int): The maximum number of outbox records to claim.
        Returns:
            A list of domain events parsed from the claimed outbox records.
        """

        stmt = (
            select(OutboxRecord)
            .where(OutboxRecord.published == False)  # noqa: E712
            .with_for_update(skip_locked=True)
            .limit(batch)
        )

        rows = await self._session.scalars(stmt)

        return [DomainEvent.from_dict(row.body) for row in rows]

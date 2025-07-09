from abc import ABC, abstractmethod

from app.domains.event import DomainEvent


class OutboxRepository(ABC):
    @abstractmethod
    async def store(
        self,
        events: list[DomainEvent],
        *,
        caused_by: str | None = None,
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

from app.contracts.repositories.outbox import OutboxRepository
from app.infra.database.repositories.base import BasePostgresRepository
from app.domains.event import DomainEvent


class PostgresOutboxRepository(OutboxRepository, BasePostgresRepository):
    async def store(
        self, events: list[DomainEvent], *, caused_by: str | None = None
    ) -> None:
        raise NotImplementedError

from uuid import UUID

from app.domains.event import DomainEvent
from app.schemas.base import BaseSchema


class OutboxDTO(BaseSchema):
    id: UUID
    caused_by: str
    event: DomainEvent

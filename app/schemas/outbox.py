from uuid import UUID

from app.domains.event import DomainEvent
from app.schemas.base import BaseSchema


class OutboxDTO(BaseSchema):
    id: UUID
    caused_by: str
    event: DomainEvent
    attempts: int


class OutboxPublishResult(BaseSchema):
    record: OutboxDTO
    success: bool
    error: str | None


class OutboxProcessingResult(OutboxPublishResult):
    attempts: int


class CreateBotDeliveryTask(BaseSchema):
    outbox_id: UUID
    subscription_id: UUID


class BotDeliveryTaskDTO(BaseSchema):
    id: UUID
    outbox_id: UUID
    subscription_id: UUID


class PublishBotDeliveryTask(BaseSchema):
    event: DomainEvent

    telegram_id: str

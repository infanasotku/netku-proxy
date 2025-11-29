from uuid import UUID

from pydantic import BaseModel


class EngineSubscriptionDTO(BaseModel):
    id: UUID
    engine_id: UUID
    user_id: UUID

    event: str


class CreateEngineSubscription(BaseModel):
    engine_id: UUID
    user_id: UUID

    event: str

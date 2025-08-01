from datetime import datetime
from uuid import UUID

from app.schemas import BaseSchema


class EngineCmd(BaseSchema):
    id: UUID
    created: datetime
    running: bool = False
    uuid: UUID | None = None
    addr: str

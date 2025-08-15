from datetime import datetime
from uuid import UUID

from app.schemas import BaseSchema


class EngineInfoDTO(BaseSchema):
    id: UUID
    created: datetime
    running: bool = False
    uuid: UUID | None = None
    addr: str


class EngineCmd(EngineInfoDTO):
    pass

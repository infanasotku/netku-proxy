from pydantic import BaseModel


class AiogramSettings(BaseModel):
    token: str
    secret: str

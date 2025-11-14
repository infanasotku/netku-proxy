from pydantic import BaseModel


class AiogramSettings(BaseModel):
    url: str
    token: str
    secret: str

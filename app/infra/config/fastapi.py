from pydantic import Field, BaseModel


class FastAPISettings(BaseModel):
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5100)

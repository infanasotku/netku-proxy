from pydantic import Field, BaseModel, computed_field


class RedisSettings(BaseModel):
    password: str | None = Field(default=None)
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5672)
    db: int = Field(default=0)

    @computed_field
    @property
    def dsn(self) -> str:
        creds = f":{self.password}" if self.password is not None else ""
        return f"redis://{creds}@{self.host}:{self.port}/"

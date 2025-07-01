from pydantic import Field, BaseModel, computed_field


class RabbitMQSettings(BaseModel):
    username: str
    password: str
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5672)

    @computed_field
    @property
    def dsn(self) -> str:
        return f"amqp://{self.username}:{self.password}@{self.host}:{self.port}/"

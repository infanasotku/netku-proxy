from pydantic import Field, BaseModel, computed_field


class PostgreSQLSettings(BaseModel):
    password: str
    username: str
    sql_schema: str = Field(default="public")
    host: str = Field(default="127.0.0.1")
    port: int = Field(default=5432)
    db_name: str = Field(default="postgres")

    @computed_field
    @property
    def dsn(self) -> str:
        return (
            f"postgresql+asyncpg://{self.username}:{self.password}"
            + f"@{self.host}:{self.port}/{self.db_name}"
        )

import os

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.infra.config.admin import AdminSettings
from app.infra.config.aiogram import AiogramSettings
from app.infra.config.postgres import PostgreSQLSettings
from app.infra.config.rabbitmq import RabbitMQSettings
from app.infra.config.redis import RedisSettings
from app.infra.config.sentry import SentrySettings
from app.infra.config.ssl import SSLSettings


class Settings(BaseSettings):
    admin: AdminSettings
    postgres: PostgreSQLSettings
    rabbit: RabbitMQSettings
    redis: RedisSettings
    ssl: SSLSettings = Field(default_factory=SSLSettings)
    sentry: SentrySettings
    aiogram: AiogramSettings

    rabbit_scope_vhost: str = Field()
    rabbit_proxy_vhost: str = Field()

    model_config = SettingsConfigDict(env_nested_delimiter="__")


def _generate_settings():
    load_dotenv(override=True, dotenv_path=os.getcwd() + "/.env")
    return Settings()  # type: ignore


settings = _generate_settings()

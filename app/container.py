from typing import Awaitable, TypeVar

from dependency_injector import containers, providers
from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.aiogram import get_bot
from app.infra.aiogram.event import AiogramEventPublisher
from app.infra.database.uow import PgCommonUnitOfWork
from app.infra.grpc.channel import generate_create_channel_context
from app.infra.grpc.engine import create_grpc_manager
from app.infra.logging import logger
from app.infra.redis.broker import get_redis, get_redis_broker
from app.services.billing import BillingService
from app.services.engine import EngineService
from app.services.outbox import OutboxService

ResourceT = TypeVar("ResourceT")


class EventsResource(providers.Resource[ResourceT]):
    pass


class ApiResource(providers.Resource):
    pass


class OutboxResource(providers.Resource[ResourceT]):
    pass


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    logger = providers.Object(logger)

    async_engine = providers.Singleton(
        create_async_engine,
        config.postgres.dsn,
        connect_args=providers.Dict(
            server_settings=providers.Dict(search_path=config.postgres.sql_schema)
        ),
        pool_pre_ping=True,
        pool_recycle=3600,
    )
    async_sessionmaker = providers.Singleton(
        async_sessionmaker[AsyncSession], async_engine
    )
    redis_broker = EventsResource[Awaitable[RedisBroker]](
        get_redis_broker,  # type: ignore
        config.redis.dsn,
        db=config.redis.db,
        logger=logger,
    )
    redis = providers.Singleton(
        get_redis,
        redis_broker,
    )
    create_channel_context = providers.Singleton(
        generate_create_channel_context,
        logger,
        with_cert=True,
        root_certificates=config.ssl.root_certificates,
    )
    bot = providers.Singleton(
        get_bot,
        config.aiogram.token,
    )

    engine_manager = ApiResource(create_grpc_manager, create_channel_context)
    event_publisher = providers.Singleton(AiogramEventPublisher, bot)

    uow = providers.Factory(PgCommonUnitOfWork, async_sessionmaker)

    billing_service = providers.Factory(
        BillingService,
        uow,
    )
    engine_service = providers.Factory(
        EngineService, uow, engine_manager, logger=logger
    )
    outbox_service = providers.Factory(
        OutboxService,
        uow,
        billing_service,
        event_publisher,
    )

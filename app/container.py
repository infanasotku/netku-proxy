from typing import Awaitable, TypeVar

from dependency_injector import containers, providers
from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.aiogram import get_bot
from app.infra.aiogram.event import AiogramEventPublisher
from app.infra.database.uows.billing import PgBillingUnitOfWork
from app.infra.database.uows.engine import PgEngineUnitOfWork
from app.infra.database.uows.outbox import PgOutboxUnitOfWork
from app.infra.grpc.channel import generate_create_channel_context
from app.infra.grpc.engine import create_grpc_manager
from app.infra.logging import logger
from app.infra.redis.broker import get_redis, get_redis_broker
from app.services.billing import BillingService
from app.services.delivery import BotDeliveryTaskService
from app.services.engine import EngineService
from app.services.fanout import BotTaskFanoutPlanner
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

    plain_engine = providers.Singleton(
        create_async_engine,
        config.postgres.dsn,
        connect_args=providers.Dict(
            server_settings=providers.Dict(search_path=config.postgres.sql_schema)
        ),
        pool_pre_ping=False,
        pool_recycle=3600,
        isolation_level="AUTOCOMMIT",
    )
    tx_engine = providers.Singleton(
        create_async_engine,
        config.postgres.dsn,
        connect_args=providers.Dict(
            server_settings=providers.Dict(search_path=config.postgres.sql_schema)
        ),
        pool_pre_ping=False,
        pool_recycle=3600,
    )
    plain_sessionmaker = providers.Singleton(
        async_sessionmaker[AsyncSession], plain_engine
    )
    tx_sessionmaker = providers.Singleton(async_sessionmaker[AsyncSession], tx_engine)
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
    event_publisher = providers.Singleton(AiogramEventPublisher, bot, logger=logger)

    engine_uow = providers.Factory(
        PgEngineUnitOfWork,
        plain_sessionmaker=plain_sessionmaker,
        tx_sessionmaker=tx_sessionmaker,
    )
    outbox_uow = providers.Factory(
        PgOutboxUnitOfWork,
        plain_sessionmaker=plain_sessionmaker,
        tx_sessionmaker=tx_sessionmaker,
    )
    billing_uow = providers.Factory(
        PgBillingUnitOfWork,
        plain_sessionmaker=plain_sessionmaker,
        tx_sessionmaker=tx_sessionmaker,
    )

    billing_service = providers.Factory(
        BillingService,
        billing_uow,
    )
    bot_fanout_planner = providers.Factory(
        BotTaskFanoutPlanner, billing_service=billing_service, logger=logger
    )
    delivery_task_service = providers.Factory(
        BotDeliveryTaskService,
        outbox_uow,
        billing_service,
        event_publisher,
        logger=logger,
    )
    engine_service = providers.Factory(
        EngineService, engine_uow, engine_manager, logger=logger
    )
    outbox_service = providers.Factory(
        OutboxService, outbox_uow, bot_fanout_planner, logger=logger
    )

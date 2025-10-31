from typing import Awaitable, TypeVar

from dependency_injector import containers, providers
from faststream.rabbit import RabbitBroker, RabbitQueue
from faststream.redis import RedisBroker
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.infra.database.uow import PgEngineUnitOfWork
from app.infra.grpc.channel import generate_create_channel_context
from app.infra.grpc.engine import create_grpc_manager
from app.infra.logging import logger
from app.infra.rabbit import queues
from app.infra.rabbit.broker import get_rabbit_broker
from app.infra.rabbit.publisher import RabbitOutboxPublisher
from app.infra.redis.broker import get_redis, get_redis_broker
from app.services.engine import EngineService
from app.services.outbox import OutboxService


def get_rabbit_publisher(broker: RabbitBroker, *, queue: RabbitQueue):
    return broker.publisher(queue)


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
    rabbit_broker = OutboxResource[Awaitable[RabbitBroker]](
        get_rabbit_broker,  # type: ignore
        config.rabbit.dsn,
        virtualhost=config.rabbit_proxy_vhost,
    )
    rabbit_publisher = providers.Singleton(
        get_rabbit_publisher, rabbit_broker, queue=queues.proxy_engine_queue
    )

    engine_manager = ApiResource(create_grpc_manager, create_channel_context)
    rabbit_op = providers.Singleton(RabbitOutboxPublisher, rabbit_publisher)

    uow = providers.Factory(PgEngineUnitOfWork, async_sessionmaker)

    engine_service = providers.Factory[Awaitable[EngineService]](
        EngineService,  # type: ignore
        uow,
        engine_manager,
    )
    outbox_service = providers.Factory[Awaitable[OutboxService]](
        OutboxService,  # type: ignore
        uow,
        rabbit_op,
    )

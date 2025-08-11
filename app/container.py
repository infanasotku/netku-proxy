from typing import Awaitable, Generic, TypeVar

from dependency_injector import providers, containers
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from faststream.rabbit import RabbitBroker, RabbitQueue, utils
from faststream.redis import RedisBroker

from app.services.engine import EngineService
from app.services.outbox import OutboxService
from app.infra.logging import logger
from app.infra.database.uow import PostgresEngineUnitOfWork, PostgresOutboxUnitOfWork
from app.infra.grpc.engine import create_grpc_manager
from app.infra.grpc.channel import generate_create_channel_context
from app.infra.rabbit.publisher import RabbitOutboxPublisher
from app.infra.rabbit import queues


async def get_rabbit_broker(dsn: str, *, virtualhost: str | None = None):
    if virtualhost is not None and virtualhost.startswith("/"):
        virtualhost = "/" + virtualhost
    broker = RabbitBroker(
        dsn,
        virtualhost=virtualhost,
        publisher_confirms=True,
        # Heartbeat interval set to 20 seconds to balance timely detection of dead connections
        # and avoid excessive network traffic. This value helps maintain connection reliability
        # without causing unnecessary disconnects due to transient network issues.
        client_properties=utils.RabbitClientProperties(heartbeat=20),
    )
    await broker.connect()
    try:
        yield broker
    finally:
        await broker.stop()


def get_rabbit_publisher(broker: RabbitBroker, *, queue: RabbitQueue):
    return broker.publisher(queue)


async def get_redis_broker(dsn: str, *, db: int = 0):
    broker = RedisBroker(dsn, db=db)
    await broker.connect()
    try:
        yield broker
    finally:
        await broker.stop()


async def get_redis(broker: RedisBroker):
    return await broker.connect()


ResourceT = TypeVar("ResourceT")


class EventsResource(providers.Resource[ResourceT], Generic[ResourceT]):
    pass


class ApiResource(providers.Resource):
    pass


class OutboxResource(providers.Resource[ResourceT], Generic[ResourceT]):
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

    engine_uow = providers.Factory(PostgresEngineUnitOfWork, async_sessionmaker)
    outbox_uow = providers.Factory(PostgresOutboxUnitOfWork, async_sessionmaker)

    engine_service = providers.Factory[Awaitable[EngineService]](
        EngineService,  # type: ignore
        engine_uow,
        engine_manager,
    )
    outbox_service = providers.Factory[Awaitable[OutboxService]](
        OutboxService,  # type: ignore
        outbox_uow,
        rabbit_op,
    )

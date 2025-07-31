from dependency_injector import providers, containers
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from faststream.rabbit import RabbitBroker
from faststream.redis import RedisBroker

from app.services.engine import EngineService
from app.services.outbox import OutboxService
from app.infra.logging import logger
from app.infra.database.uow import PostgresEngineUnitOfWork, PostgresOutboxUnitOfWork
from app.infra.grpc.engine import create_grpc_manager
from app.infra.grpc.channel import generate_create_channel_context
from app.infra.rabbit.publisher import RabbitPublisher
from app.infra.rabbit import queues


async def get_broker(dsn: str, *, virtualhost: str | None = None):
    if virtualhost is not None and virtualhost.startswith("/"):
        virtualhost = "/" + virtualhost
    broker = RabbitBroker(dsn, virtualhost=virtualhost, publisher_confirms=True)
    await broker.connect()
    yield broker
    await broker.stop()


async def get_redis(dsn: str, *, db: int = 0):
    broker = RedisBroker(dsn, db=db)
    redis = await broker.connect()
    yield redis
    await broker.stop()


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
    redis = providers.Resource(get_redis, config.redis.dsn, db=config.redis.db)
    create_channel_context = providers.Singleton(
        generate_create_channel_context,
        logger,
        with_cert=True,
        root_certificates=config.ssl.root_certificates,
    )
    rabbit_broker = providers.Resource(
        get_broker, config.rabbit.dsn, virtualhost=config.rabbit_proxy_vhost
    )

    engine_manager = providers.Resource(create_grpc_manager, create_channel_context)
    rabbit_publisher = providers.Singleton(
        RabbitPublisher, rabbit_broker, queue=queues.proxy_engine_queue
    )

    engine_uow = providers.Factory(PostgresEngineUnitOfWork, async_sessionmaker)
    outbox_uow = providers.Factory(PostgresOutboxUnitOfWork, async_sessionmaker)

    engine_service = providers.Factory(EngineService, engine_uow, engine_manager)
    outbox_service = providers.Factory(
        OutboxService,
        outbox_uow,
        rabbit_publisher,
    )

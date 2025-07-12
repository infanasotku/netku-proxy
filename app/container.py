from dependency_injector import providers, containers
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from faststream.rabbit import RabbitBroker
from faststream.redis import RedisBroker

from app.services.engine import EngineServiceImpl
from app.infra.logging import logger
from app.infra.database.uow import PostgresEngineUnitOfWork
from app.infra.grpc.engine import create_grpc_manager
from app.infra.grpc.channel import generate_create_channel_context


async def get_broker(dsn: str, *, virtualhost: str | None = None):
    broker = RabbitBroker(dsn, virtualhost=virtualhost)
    await broker.connect()
    yield broker
    await broker.close()


async def get_redis(dsn: str):
    broker = RedisBroker(dsn)
    redis = await broker.connect()
    yield redis
    await broker.close()


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
    redis = providers.Resource(get_redis, config.redis.dsn)
    create_channel_context = providers.Singleton(
        generate_create_channel_context, logger, with_cert=True
    )

    broker = providers.Resource(
        get_broker, config.rabbit.dsn, virtualhost=config.rabbit_proxy_vhost
    )

    engine_manager = providers.Resource(create_grpc_manager, create_channel_context)

    uow = providers.Factory(PostgresEngineUnitOfWork, async_sessionmaker)

    engine_service = providers.Singleton(EngineServiceImpl, uow, engine_manager)

from dependency_injector import providers, containers
from faststream.rabbit import RabbitBroker
from faststream.redis import RedisBroker

from app.services.proxy import ProxyServiceImpl
from app.infra.logging import logger


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

    redis = providers.Resource(get_redis, config.redis.dsn)

    broker = providers.Resource(
        get_broker, config.rabbit.dsn, virtualhost=config.rabbit_proxy_vhost
    )

    proxy_service = providers.Singleton(ProxyServiceImpl)

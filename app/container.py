from dependency_injector import providers, containers
from faststream.rabbit import RabbitBroker

from app.infra.logging import logger


async def get_broker(dsn: str, *, virtualhost: str | None = None):
    broker = RabbitBroker(dsn, virtualhost=virtualhost)
    await broker.connect()
    yield broker
    await broker.close()


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    logger = providers.Object(logger)

    broker = providers.Resource(
        get_broker, config.rabbit.dsn, virtualhost=config.rabbit_proxy_vhost
    )

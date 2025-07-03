from dependency_injector import providers, containers
from faststream.rabbit import RabbitBroker

from app.infra.logging import logger


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    logger = providers.Object(logger)

    broker = providers.Singleton(
        RabbitBroker,
        config.rabbit.dsn,
        virtualhost=config.rabbit_proxy_vhost,
    )

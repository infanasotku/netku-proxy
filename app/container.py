from dependency_injector import providers, containers

from app.infra.logging import logger


class Container(containers.DeclarativeContainer):
    config = providers.Configuration()
    logger = providers.Object(logger)

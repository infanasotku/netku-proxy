from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from app.infra.config import settings
from app.infra.logging import logger
from app.container import Container


def create_lifespan(scope_broker: RabbitBroker):
    @asynccontextmanager
    async def lifespan(_):
        try:
            await scope_broker.start()
            yield
        finally:
            await scope_broker.close()

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)

    proxy_broker = container.rabbit_proxy_broker()
    scope_broker = RabbitBroker(
        settings.rabbit.dsn,
        virtualhost=settings.rabbit_scope_vhost,
    )

    app = FastStream(
        proxy_broker, logger=logger, lifespan=create_lifespan(scope_broker)
    ).as_asgi(asyncapi_path="/docs")
    app.__dict__["container"] = container

    return app


app = create_app()

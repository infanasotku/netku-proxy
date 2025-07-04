from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.redis import RedisBroker

from app.infra.config import settings
from app.infra.logging import logger
from app.container import Container

from app.controllers.events import engine


def create_lifespan(container: Container):
    @asynccontextmanager
    async def lifespan(_):
        future = container.init_resources()
        if future is not None:
            await future

        yield
        future = container.shutdown_resources()
        if future is not None:
            await future

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)

    engine_broker = RedisBroker(settings.redis.dsn, logger=logger)
    engine_broker.include_router(engine.router)

    app = FastStream(
        engine_broker,
        logger=logger,
        lifespan=create_lifespan(container),
        title="Proxy events",
        version="",
        identifier="urn:events",
    ).as_asgi(asyncapi_path=None)
    app.__dict__["container"] = container

    return app


app = create_app()

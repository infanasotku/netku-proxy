from contextlib import asynccontextmanager

from faststream.asgi import make_ping_asgi
from faststream import FastStream
from faststream.redis import RedisBroker
from dependency_injector import providers

from app.infra.config import settings
from app.infra.sentry import init_sentry
from app.infra.logging import logger
from app.container import Container

from app.controllers.events import engine


def create_lifespan(container: Container, engine_broker: RedisBroker):
    @asynccontextmanager
    async def lifespan(_):
        redis = await engine_broker.connect()  # For getting redis instance
        container.redis.override(providers.Singleton(lambda: redis))

        future = container.init_resources()
        if future is not None:
            await future

        async with engine.start_keyevents_reclaimer(redis, logger):
            yield

        future = container.shutdown_resources()
        if future is not None:
            await future

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "app.controllers.events.engine",
        ]
    )

    init_sentry()

    engine_broker = RedisBroker(settings.redis.dsn, logger=logger)
    engine_broker.include_router(engine.router)

    app = FastStream(
        engine_broker,
        logger=logger,
        lifespan=create_lifespan(container, engine_broker),
        title="Proxy events",
        version="",
        identifier="urn:events",
    ).as_asgi(
        asyncapi_path=None,
        asgi_routes=[("/healthz", make_ping_asgi(engine_broker, timeout=5.0))],
    )
    app.__dict__["container"] = container

    return app


app = create_app()

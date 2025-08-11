from contextlib import asynccontextmanager

from faststream.asgi import make_ping_asgi
from faststream import FastStream

from app.infra.config import settings
from app.infra.sentry import init_sentry
from app.infra.logging import logger
from app.container import Container, EventsResource

from app.controllers.events import engine


def create_lifespan(container: Container, app):
    async def _maybe_future(future):
        if future is not None:
            await future

    @asynccontextmanager
    async def lifespan():
        engine_broker = await container.redis_broker()
        engine_broker.include_router(engine.router)

        app.mount("/healthz", make_ping_asgi(engine_broker, timeout=5.0))
        app.broker = engine_broker

        redis = await container.redis()

        await _maybe_future(container.init_resources(EventsResource))
        async with engine.start_keyevents_reclaimer(redis, logger):
            yield
        await _maybe_future(container.shutdown_resources(EventsResource))

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

    app = FastStream(
        None,
        logger=logger,
        title="Proxy events",
        version="",
        identifier="urn:events",
    ).as_asgi(
        asyncapi_path=None,
    )
    app.lifespan_context = create_lifespan(container, app)
    app.__dict__["container"] = container

    return app


app = create_app()

from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from app.infra.config import settings
from app.infra.logging import logger
from app.infra.rabbit.exchanges import dlx_exchange
from app.infra.rabbit.queues import dead_letter_queue
from app.container import Container

from app.controllers.events import scope


def create_lifespan(scope_broker: RabbitBroker, broker: RabbitBroker):
    @asynccontextmanager
    async def lifespan(_):
        try:
            await broker.connect()
            await scope_broker.start()

            ex = await broker.declare_exchange(dlx_exchange)
            q = await broker.declare_queue(dead_letter_queue)
            await q.bind(ex, routing_key=dead_letter_queue.routing_key)

            yield
        finally:
            await broker.close()
            await scope_broker.close()

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)

    broker = container.broker()

    scope_broker = RabbitBroker(
        settings.rabbit.dsn, virtualhost=settings.rabbit_scope_vhost, logger=logger
    )
    scope_broker.include_router(scope.router)

    app = FastStream(
        broker,
        logger=logger,
        lifespan=create_lifespan(scope_broker, broker),
    ).as_asgi(asyncapi_path="/docs")
    app.__dict__["container"] = container

    return app


app = create_app()

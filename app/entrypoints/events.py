from contextlib import asynccontextmanager

from faststream import FastStream
from faststream.rabbit import RabbitBroker

from app.infra.config import settings
from app.infra.logging import logger
from app.infra.rabbit.exchanges import dlx_exchange
from app.infra.rabbit.queues import dead_letter_queue
from app.container import Container


def create_lifespan(scope_broker: RabbitBroker, proxy_broker: RabbitBroker):
    @asynccontextmanager
    async def lifespan(_):
        try:
            await scope_broker.start()
            await proxy_broker.start()

            ex = await proxy_broker.declare_exchange(dlx_exchange)
            q = await proxy_broker.declare_queue(dead_letter_queue)
            await q.bind(ex, routing_key=dead_letter_queue.routing_key)

            yield
        finally:
            await scope_broker.close()
            await proxy_broker.close()

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
        proxy_broker,
        logger=logger,
        lifespan=create_lifespan(scope_broker, proxy_broker),
    ).as_asgi(asyncapi_path="/docs")
    app.__dict__["container"] = container

    return app


app = create_app()

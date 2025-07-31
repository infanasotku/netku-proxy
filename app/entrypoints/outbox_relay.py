from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.config import settings
from app.infra.logging import logger
from app.infra.rabbit import queues, exchanges
from app.container import Container

from app.controllers.outbox import relay


def create_lifespan(container: Container):
    async def _maybe_future(future):
        if future is not None:
            await future

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await _maybe_future(container.init_resources())

        broker = await container.rabbit_broker()
        exc = await broker.declare_exchange(exchanges.dlx_exchange)
        dlq = await broker.declare_queue(queues.dead_letter_queue)
        await dlq.bind(exc, routing_key=queues.dead_letter_queue.routing_key)
        await broker.declare_queue(queues.proxy_engine_queue)

        async with relay.start_outbox_relay(logger):
            yield

        await _maybe_future(container.shutdown_resources())

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "app.controllers.outbox.relay",
        ]
    )

    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan(container))
    app.__dict__["container"] = container
    return app


app = create_app()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

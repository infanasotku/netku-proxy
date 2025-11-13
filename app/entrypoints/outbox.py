from contextlib import asynccontextmanager

from fastapi import FastAPI
from sentry_sdk.types import Event

from app.container import Container, OutboxResource
from app.controllers.outbox import relay
from app.infra.config import settings
from app.infra.sentry import init_sentry


def before_send_transaction(event: Event, _):
    tags = event.get("tags") or {}
    if tags.get("empty_batch") == "1":
        return None  # skip transaction
    return event


def create_lifespan(container: Container):
    async def _maybe_future(future):
        if future is not None:
            await future

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await _maybe_future(container.init_resources(OutboxResource))

        async with relay.start_outbox_relay():
            yield

        await _maybe_future(container.shutdown_resources(OutboxResource))

    return lifespan


def create_app():
    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "app.controllers.outbox.relay",
        ]
    )

    init_sentry(before_send_transaction=before_send_transaction)

    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan(container))
    app.__dict__["container"] = container
    return app


app = create_app()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

from contextlib import asynccontextmanager
from typing import cast

from fastapi import FastAPI
from sentry_sdk.tracing import TransactionSource
from sentry_sdk.types import Event

from app.container import ApiResource, Container
from app.controllers.admin import register_admin
from app.infra.config import settings
from app.infra.sentry import init_sentry


def before_send_transaction(event: Event, _):
    if tr_info := event.get("transaction_info"):
        source: TransactionSource = cast(TransactionSource, tr_info.get("source"))
        if source == TransactionSource.URL:
            return  # Cancel transactions for 404
    else:
        return

    return event


def traces_sampler(ctx: dict):
    scope: dict = ctx["asgi_scope"]
    path: str = scope["path"]
    method: str = scope["method"]

    if (
        path.startswith("/admin")
        and not (path.startswith("/admin/engine/edit") and method == "POST")
        and not (path.startswith("/admin/engine/action") and method == "GET")
    ):
        return 0.0

    return 1.0


def create_lifespan(container: Container):
    async def _maybe_future(future):
        if future is not None:
            await future

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        await _maybe_future(container.init_resources(ApiResource))
        yield
        await _maybe_future(container.shutdown_resources(ApiResource))

    return lifespan


def create_app() -> FastAPI:
    container = Container()
    container.config.from_pydantic(settings)
    container.wire(
        modules=[
            "app.controllers.admin.main",
            "app.controllers.admin.views",
        ]
    )

    init_sentry(
        traces_sampler=traces_sampler, before_send_transaction=before_send_transaction
    )

    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan(container))
    app.__dict__["container"] = container

    register_admin(
        app,
        username=settings.admin.username,
        password=settings.admin.password,
        secret=settings.admin.secret,
    )

    return app


app = create_app()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

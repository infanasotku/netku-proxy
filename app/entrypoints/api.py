from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.config import settings
from app.container import Container

from app.controllers.admin import register_admin


def create_lifespan(container: Container):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        future = container.init_resources()
        if future is not None:
            await future

        yield

        future = container.shutdown_resources()
        if future is not None:
            await future

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

    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan(container))
    app.__dict__["container"] = container

    register_admin(
        app, username=settings.admin.username, password=settings.admin.password
    )

    return app


app = create_app()


@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.infra.config import settings
from app.container import Container


def create_lifespan(container: Container):
    @asynccontextmanager
    async def lifespan(_: FastAPI):
        yield

    return lifespan


def create_app() -> FastAPI:
    container = Container()
    container.config.from_pydantic(settings)

    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan(container))
    app.__dict__["container"] = container

    return app


app = create_app()

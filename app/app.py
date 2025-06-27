from fastapi import FastAPI


def create_lifespan():
    pass


def create_app() -> FastAPI:
    app = FastAPI(redoc_url=None, docs_url=None, lifespan=create_lifespan())

    return app


app = create_app()

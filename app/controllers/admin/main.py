from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine
from dependency_injector.wiring import Provide, inject

from app.container import Container
from app.controllers.admin.auth import AdminAuthenticationBackend
import app.controllers.admin.views as views


@inject
def register_admin(
    app: FastAPI,
    *,
    username: str,
    password: str,
    engine: AsyncEngine = Provide[Container.async_engine],
):
    authentication_backend = AdminAuthenticationBackend(
        username=username, password=password
    )
    admin = Admin(
        app,
        engine,
        title="Engine panel",
        authentication_backend=authentication_backend,
    )

    admin.add_view(views.EngineView)
    admin.add_view(views.OutboxView)

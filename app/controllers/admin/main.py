from dependency_injector.wiring import Provide, inject
from fastapi import FastAPI
from sqladmin import Admin
from sqlalchemy.ext.asyncio import AsyncEngine

import app.controllers.admin.views as views
from app.container import Container
from app.controllers.admin.auth import AdminAuthenticationBackend


@inject
def register_admin(
    app: FastAPI,
    *,
    username: str,
    password: str,
    engine: AsyncEngine = Provide[Container.async_engine],
    secret: str,
):
    authentication_backend = AdminAuthenticationBackend(
        secret, username=username, password=password
    )
    admin = Admin(
        app,
        engine,
        title="Engine panel",
        authentication_backend=authentication_backend,
        base_url="/admin",
    )

    admin.add_view(views.EngineView)
    admin.add_view(views.OutboxView)
    admin.add_view(views.BotDeliveryTaskView)
    admin.add_view(views.UserView)
    admin.add_view(views.EngineSubscriptionView)
    admin.add_view(views.UserSubscriptionGroupView)

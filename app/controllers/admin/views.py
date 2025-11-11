from logging import Logger
from uuid import UUID

from dependency_injector.wiring import Provide
from fastapi.responses import RedirectResponse
from sentry_sdk import get_current_scope
from sqladmin import ModelView, action
from sqladmin.filters import BooleanFilter, StaticValuesFilter

from app.container import Container
from app.domains.engine import EngineStatus
from app.infra.database import models
from app.services.engine import EngineService


class EngineView(ModelView, model=models.Engine):
    can_export = True
    can_edit = True
    can_delete = False
    can_create = False
    name_plural = "Engines"

    column_list = [
        models.Engine.id,
        models.Engine.uuid,
        models.Engine.addr,
        models.Engine.status,
        models.Engine.created,
    ]

    form_columns = [models.Engine.uuid]

    column_sortable_list = [
        models.Engine.created,
    ]

    column_filters = [
        StaticValuesFilter(
            models.Engine.status,
            [
                ("DEAD", EngineStatus.DEAD),
                ("ACTIVE", EngineStatus.ACTIVE),
                ("READY", EngineStatus.READY),
            ],
        )
    ]

    async def update_model(
        self,
        request,
        pk,
        data,
        engine_service: EngineService = Provide[Container.engine_service],
        logger: Logger = Provide[Container.logger],
    ) -> models.Engine:
        scope = get_current_scope()
        path_format, _, _ = request.scope["path"].rpartition("/")
        path_format += "/{engine_id}"
        scope.set_transaction_name(f"{request.method} {path_format}")

        uuid = UUID(data["uuid"])
        id = UUID(pk)

        try:
            await engine_service.restart(id, uuid=uuid)
        except Exception:
            logger.error(
                f"Error occured while restarting engine with ID {id}:",
            )
            raise

        return models.Engine()

    @action(
        name="remove_dead_engines",
        label="Remove dead engines",
        confirmation_message="Are you sure?",
        add_in_detail=False,
        add_in_list=True,
    )
    async def remove_dead_engines(
        self,
        request,
        engine_service: EngineService = Provide[Container.engine_service],
        logger: Logger = Provide[Container.logger],
    ):
        scope = get_current_scope()
        path_format, _, _ = request.scope["path"].rpartition("/")
        path_format += "/{action}"
        scope.set_transaction_name(f"{request.method} {path_format}")

        try:
            await engine_service.remove_dead_engines()
        except Exception:
            logger.error("Error occurred while removing dead engines.")
            raise

        return RedirectResponse(request.url_for("admin:list", identity=self.identity))


class OutboxView(ModelView, model=models.Outbox):
    name_plural = "Outbox"

    can_delete = False
    can_create = False
    can_edit = False
    can_export = True

    column_list = [
        models.Outbox.id,
        models.Outbox.caused_by,
        models.Outbox.created_at,
        models.Outbox.fanned_out,
        models.Outbox.fanned_out_at,
        models.Outbox.attempts,
        models.Outbox.body,
    ]

    column_sortable_list = [
        models.Outbox.created_at,
        models.Outbox.fanned_out_at,
    ]

    column_filters = [BooleanFilter(models.Outbox.fanned_out)]

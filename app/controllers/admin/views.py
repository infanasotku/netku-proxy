from logging import Logger
from uuid import UUID

from sqladmin import ModelView
from sqladmin.filters import StaticValuesFilter, BooleanFilter
from dependency_injector.wiring import Provide
from sentry_sdk import get_current_scope, start_span

from app.services.engine import EngineService
from app.domains.engine import EngineStatus
from app.infra.database import models
from app.container import Container


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
    ):
        scope = get_current_scope()
        path_format, _, _ = request.scope["path"].rpartition("/")
        path_format += "/{engine_id}"
        scope.set_transaction_name(f"{request.method} {path_format}")

        uuid = UUID(data["uuid"])
        id = UUID(pk)

        with start_span(op="task", description="Restart engine") as span:
            span.set_tag("engine_id", id.hex)

            try:
                await engine_service.restart(id, uuid=uuid)
                logger.info(f"Engine with ID [{id}] restarted.")
            except Exception:
                logger.error(
                    f"Error occured while restarting engine with ID {id}:",
                )
                raise

        return models.Engine()


class OutboxView(ModelView, model=models.OutboxRecord):
    name_plural = "Outbox"

    can_delete = False
    can_create = False
    can_edit = False
    can_export = True

    column_list = [
        models.OutboxRecord.id,
        models.OutboxRecord.caused_by,
        models.OutboxRecord.created_at,
        models.OutboxRecord.published,
        models.OutboxRecord.published_at,
        models.OutboxRecord.attempts,
        models.OutboxRecord.body,
    ]

    column_sortable_list = [
        models.OutboxRecord.created_at,
        models.OutboxRecord.published_at,
    ]

    column_filters = [BooleanFilter(models.OutboxRecord.published)]

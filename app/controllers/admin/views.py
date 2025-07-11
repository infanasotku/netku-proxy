from logging import Logger
from uuid import UUID
from sqladmin import ModelView
from dependency_injector.wiring import Provide


from app.contracts.services.engine import EngineService
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

    async def update_model(
        self,
        request,
        pk,
        data,
        engine_service: EngineService = Provide[Container.engine_service],
        logger: Logger = Provide[Container.logger],
    ):
        uuid = UUID(data["uuid"])
        id = UUID(pk)

        try:
            await engine_service.restart(id, uuid=uuid)
            logger.info(f"Engine with ID [{id}] restarted.")
        except Exception as e:
            logger.error(
                f"Error occured while restarting engine with ID {id}: {str(e)}",
                exc_info=True,
            )

        return models.Engine()

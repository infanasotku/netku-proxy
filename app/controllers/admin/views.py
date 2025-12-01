from logging import Logger
from typing import Any, cast
from uuid import UUID

import wtforms
from dependency_injector.wiring import Provide, inject
from fastapi import Request
from fastapi.responses import RedirectResponse
from markupsafe import Markup
from sentry_sdk import get_current_scope
from sqladmin import Admin, ModelView, action
from sqladmin.filters import BooleanFilter, StaticValuesFilter
from sqladmin.helpers import slugify_class_name

from app.container import Container
from app.domains.engine import EngineDead, EngineRestored, EngineStatus, EngineUpdated
from app.infra.database import aggregates, models
from app.services.billing import BillingService
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
    column_details_list = [
        *column_list,
        models.Engine.subscriptions,
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

    @inject
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

    can_delete = True
    can_create = False
    can_edit = True
    can_export = True

    column_list = "__all__"

    column_sortable_list = [
        models.Outbox.created_at,
        models.Outbox.fanned_out_at,
    ]

    column_filters = [BooleanFilter(models.Outbox.fanned_out)]


class BotDeliveryTaskView(ModelView, model=models.BotDeliveryTask):
    name_plural = "Bot Delivery Tasks"

    can_delete = True
    can_create = False
    can_edit = True
    can_export = True

    column_list = "__all__"

    column_sortable_list = [models.BotDeliveryTask.created_at]

    column_filters = [BooleanFilter(models.BotDeliveryTask.published)]


class UserView(ModelView, model=models.User):
    name_plural = "Users"

    can_delete = True
    can_create = True
    can_edit = True
    can_export = True

    column_list = [
        models.User.telegram_id,
        models.User.description,
    ]
    column_details_list = [
        *column_list,
        models.Engine.subscriptions,
    ]

    form_columns = [
        models.User.telegram_id,
        models.User.description,
    ]


engine_events = (EngineDead, EngineUpdated, EngineRestored)


class EngineSubscriptionView(ModelView, model=models.EngineSubscription):
    name_plural = "Engine Subscriptions"

    can_delete = True
    can_create = True
    can_edit = True
    can_export = True

    column_list = [
        models.EngineSubscription.user,
        models.EngineSubscription.engine,
        models.EngineSubscription.event,
    ]
    column_details_list = column_list

    form_args = dict(
        event=dict(
            choices=[(ev.__name__, ev.__name__) for ev in engine_events],
            coerce=str,
        ),
    )
    form_overrides = dict(event=wtforms.SelectField)
    form_columns = column_list


class UserSubscriptionGroupView(ModelView, model=aggregates.UserSubscriptionGroup):
    column_list = [
        aggregates.UserSubscriptionGroup.user,
        aggregates.UserSubscriptionGroup.engine,
        "events",
    ]
    column_details_list = column_list

    column_formatters = {
        "events": lambda m, a: m,
    }
    column_formatters_detail = column_formatters

    form_columns = ["user", "engine"]

    def __init__(self):
        super().__init__()
        self._list_formatters["events"] = self._events_formatter
        self._detail_formatters["events"] = self._events_formatter

    def _events_formatter(self, obj, attr):
        admin = cast(Admin, self._admin_ref)

        identity = slugify_class_name(models.EngineSubscription.__name__)

        ids = getattr(obj, "subscription_ids", None) or []
        events = getattr(obj, "events", None) or []

        links: list[str] = []

        for sub_id, event in zip(ids, events):
            path = admin.app.url_path_for(
                "admin:details",
                identity=identity,
                pk=str(sub_id),
            )
            links.append(f'<a href="{path}">{event}</a>')

        return Markup("<br>".join(links))

    async def scaffold_form(self, rules: list[str] | None = None):
        form_class = await super().scaffold_form(rules)

        setattr(
            form_class,
            "events",
            wtforms.SelectMultipleField(
                choices=[(ev.__name__, ev.__name__) for ev in engine_events],
                coerce=str,
                render_kw={"class": "form-control"},
            ),
        )

        if rules:
            self._validate_form_class(rules, form_class)

        return form_class

    @inject
    async def update_model(
        self,
        request: Request,
        pk: str,
        data: dict,
        svc: BillingService = Provide[Container.billing_service],
    ) -> Any:
        user_id = UUID(data["user"])
        engine_id = UUID(data["engine"])
        events: list[str] = data["events"]

        await svc.upsert_subscriptions(events, user_id=user_id, engine_id=engine_id)
        return aggregates.UserSubscriptionGroup()

    @inject
    async def insert_model(
        self,
        request: Request,
        data: dict,
        svc: BillingService = Provide[Container.billing_service],
    ) -> Any:
        user_id = UUID(data["user"])
        engine_id = UUID(data["engine"])
        events: list[str] = data["events"]

        await svc.upsert_subscriptions(events, user_id=user_id, engine_id=engine_id)
        return aggregates.UserSubscriptionGroup()

    @inject
    async def delete_model(
        self,
        request: Request,
        pk: Any,
        svc: BillingService = Provide[Container.billing_service],
    ):
        user_id, engine_id = pk.split(";")
        await svc.upsert_subscriptions(
            [], user_id=UUID(user_id), engine_id=UUID(engine_id)
        )

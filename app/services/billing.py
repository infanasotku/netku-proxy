from uuid import UUID

from app.domains.event import DomainEvent
from app.infra.database.uow import PgBillingUnitOfWorkContext, PgUnitOfWork


class BillingService:
    def __init__(self, uow: PgUnitOfWork[PgBillingUnitOfWorkContext]) -> None:
        self._uow = uow

    async def get_subscriptions_for_events(
        self, events: list[DomainEvent]
    ) -> dict[str, list[UUID]]:
        async with self._uow.begin() as ctx:
            return await ctx.subscriptions.get_engine_subscriptions_for_events(events)

    async def get_telegram_ids_for_subscriptions(
        self, subscription_ids: list[UUID]
    ) -> list[str]:
        async with self._uow.begin() as ctx:
            return await ctx.subscriptions.get_telegram_ids_for_subscriptions(
                subscription_ids
            )

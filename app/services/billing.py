from uuid import UUID

from app.domains.event import DomainEvent
from app.infra.database.uows import (
    PgBillingTxUOWContext,
    PgBillingUOWContext,
    PgUnitOfWork,
)
from app.schemas.billing import CreateEngineSubscription


class BillingService:
    def __init__(
        self, uow: PgUnitOfWork[PgBillingUOWContext, PgBillingTxUOWContext]
    ) -> None:
        self._uow = uow

    async def get_subscriptions_for_events(
        self, events: list[DomainEvent]
    ) -> dict[DomainEvent, list[UUID]]:
        async with self._uow.begin(with_tx=False) as ctx:
            return await ctx.subscriptions.get_engine_subscriptions_for_events(events)

    async def get_telegram_ids_for_subscriptions(
        self, subscription_ids: list[UUID]
    ) -> dict[UUID, str]:
        async with self._uow.begin(with_tx=False) as ctx:
            return await ctx.subscriptions.get_telegram_ids_for_subscriptions(
                subscription_ids
            )

    async def upsert_subscriptions(
        self, events: list[str], *, user_id: UUID, engine_id: UUID
    ) -> None:
        """Upsert subscriptions for a user and engine combination.

        Removes subscriptions that are no introduced in `events` and adds new ones.
        """

        async with self._uow.begin(with_tx=True) as ctx:
            subs = await ctx.subscriptions.get_subscriptions_by_user_and_engine(
                user_id, engine_id
            )
            existing_subs = {sub.event for sub in subs}

            for_delete = [sub.id for sub in subs if sub.event not in events]
            for_create = [ev for ev in events if ev not in existing_subs]

            await ctx.subscriptions.delete_subscriptions(for_delete)
            await ctx.subscriptions.insert_subscriptions(
                [
                    CreateEngineSubscription(
                        engine_id=engine_id,
                        user_id=user_id,
                        event=event,
                    )
                    for event in for_create
                ]
            )

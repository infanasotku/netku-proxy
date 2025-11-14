from logging import Logger

from app.infra.database.uow import PgOutboxUnitOfWorkContext
from app.schemas.outbox import CreateBotDeliveryTask, OutboxDTO
from app.services.billing import BillingService


class BotTaskFanoutPlanner:
    def __init__(self, billing_service: BillingService, *, logger: Logger) -> None:
        self._billing = billing_service
        self._logger = logger

    async def spawn_engine_delivery_tasks(
        self,
        records: list[OutboxDTO],
        *,
        ctx: PgOutboxUnitOfWorkContext,
    ):
        name_ids_dict = await self._billing.get_subscriptions_for_events(
            [rec.event for rec in records]
        )

        self._logger.info(
            f"Spawning engine delivery tasks for {len(records)} records..."
        )

        tasks = []
        for rec in records:
            ids = name_ids_dict.get(rec.event, [])
            if not ids:
                self._logger.warning(f"No subscriptions found for event {rec.event}")
                continue

            tasks.extend(
                (
                    CreateBotDeliveryTask(outbox_id=rec.id, subscription_id=id)
                    for id in ids
                )
            )

        self._logger.info(f"Spawned {len(tasks)} engine delivery tasks")

        if not tasks:
            return

        await ctx.tasks.store(tasks)

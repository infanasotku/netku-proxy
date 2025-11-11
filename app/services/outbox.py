from datetime import timedelta
from logging import Logger

from app.domains.engine import EngineDead, EngineRestored, EngineUpdated
from app.infra.aiogram.event import AiogramEventPublisher
from app.infra.database.uow import PgOutboxUnitOfWorkContext, PgUnitOfWork
from app.infra.utils.time import now_utc
from app.schemas.outbox import (
    CreateBotDeliveryTask,
    OutboxDTO,
    PublishBotDeliveryTask,
)
from app.services.billing import BillingService


class BotDeliveryTaskService:
    def __init__(
        self,
        uow: PgUnitOfWork[PgOutboxUnitOfWorkContext],
        billing_service: BillingService,
        event_publisher: AiogramEventPublisher,
        *,
        logger: Logger,
        batch=200,
        max_publish_attempts=5,
    ) -> None:
        self._uow = uow
        self._publisher = event_publisher
        self._billing = billing_service
        self._batch = batch
        self._max_attempts = max_publish_attempts
        self._logger = logger

    async def _spawn_engine_delivery_tasks(
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
            ids = name_ids_dict[rec.event.name]
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

    async def process_engine_delivery_tasks(self):
        async with self._uow.begin() as uow:
            tasks = await uow.tasks.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )
            events = await uow.outbox.extract_events([task.outbox_id for task in tasks])
            telegram_ids = await self._billing.get_telegram_ids_for_subscriptions(
                [task.subscription_id for task in tasks]
            )

            for_sending: list[PublishBotDeliveryTask] = []
            for ev, telegram_id in zip(events, telegram_ids):
                for_sending.append(
                    PublishBotDeliveryTask(event=ev, telegram_id=telegram_id)
                )

            publish_results = await self._publisher.publish_batch(for_sending)
            for success, task in zip(publish_results, tasks):
                if success:
                    await uow.tasks.mark_published(task.id)
                else:
                    next_attempt_at = now_utc() + timedelta(seconds=task.attempts**2)
                    await uow.tasks.mark_failed(next_attempt_at, task_id=task.id)

            return len(tasks)


class OutboxService(BotDeliveryTaskService):
    def __init__(
        self,
        uow: PgUnitOfWork[PgOutboxUnitOfWorkContext],
        billing_service: BillingService,
        event_publisher: AiogramEventPublisher,
        *,
        logger: Logger,
        batch=200,
        max_publish_attempts=5,
    ) -> None:
        super().__init__(
            uow,
            billing_service,
            event_publisher,
            logger=logger,
            batch=batch,
            max_publish_attempts=max_publish_attempts,
        )

    async def process_outbox_batch(self) -> int:
        async with self._uow.begin() as uow:
            records = await uow.outbox.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )

            if not records:
                return 0

            self._logger.info(f"Processing outbox batch with {len(records)} records...")

            unhandled = []
            engine_delivery_tasks = []
            for rec in records:
                match rec.event:
                    case EngineDead() | EngineRestored() | EngineUpdated():
                        engine_delivery_tasks.append(rec)
                    case _:
                        unhandled.append(rec)

            try:
                await self._spawn_engine_delivery_tasks(engine_delivery_tasks, ctx=uow)
                await self._mark_fanned_out(engine_delivery_tasks, uow=uow)
            except Exception:
                await self._mark_failed(engine_delivery_tasks, uow=uow)

            if len(engine_delivery_tasks) != len(records):
                raise NotImplementedError("Unhandled event types found")

            self._logger.info(f"Processed outbox batch with {len(records)} records")

            return len(records)

    async def _mark_failed(
        self, record: list[OutboxDTO], *, uow: PgOutboxUnitOfWorkContext
    ):
        for rec in record:
            next_attempt_at = now_utc() + timedelta(seconds=rec.attempts**2)
            await uow.outbox.mark_failed(next_attempt_at, outbox_id=rec.id)

    async def _mark_fanned_out(
        self, record: list[OutboxDTO], *, uow: PgOutboxUnitOfWorkContext
    ):
        for rec in record:
            await uow.outbox.mark_fanned_out(rec.id)

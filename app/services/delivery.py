from datetime import timedelta
from logging import Logger

from app.infra.aiogram.event import AiogramEventPublisher
from app.infra.database.uow import PgOutboxUnitOfWorkContext, PgUnitOfWork
from app.infra.utils.time import now_utc
from app.schemas.outbox import (
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

    async def process_engine_delivery_tasks(self) -> int:
        async with self._uow.begin() as uow:
            tasks = await uow.tasks.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )
            if not tasks:
                return 0

            self._logger.info(f"Processing {len(tasks)} delivery tasks")

            events = await uow.outbox.extract_events([task.outbox_id for task in tasks])
            telegram_ids = await self._billing.get_telegram_ids_for_subscriptions(
                [task.subscription_id for task in tasks]
            )

            for_sending: list[PublishBotDeliveryTask] = []
            for task in tasks:
                event = events.get(task.outbox_id)
                telegram_id = telegram_ids.get(task.subscription_id)
                if event is None or telegram_id is None:
                    self._logger.warning(
                        f"Missing data for delivery task {task.id}"
                        f"(event={event is not None} telegram={telegram_id is not None})"
                    )
                    continue

                for_sending.append(
                    PublishBotDeliveryTask(event=event, telegram_id=telegram_id)
                )

            publish_results = await self._publisher.publish_batch(for_sending)
            success_count = 0
            for success, task in zip(publish_results, tasks):
                if success:
                    await uow.tasks.mark_published(task.id)
                    success_count += 1
                else:
                    next_attempt_at = now_utc() + timedelta(seconds=task.attempts**2)
                    await uow.tasks.mark_failed(next_attempt_at, task_id=task.id)

            self._logger.info(
                f"Processed {len(tasks)} delivery tasks, success {success_count}"
            )

            return len(tasks)

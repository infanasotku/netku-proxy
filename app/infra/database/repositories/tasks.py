from datetime import datetime
from uuid import UUID

from sentry_sdk import start_span
from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert

from app.infra.database import constraints
from app.infra.database.models import BotDeliveryTask
from app.infra.database.repositories.base import PostgresRepository
from app.infra.utils.time import now_utc
from app.schemas.outbox import BotDeliveryTaskDTO, CreateBotDeliveryTask


class PgBotDeliveryTaskRepository(PostgresRepository):
    async def store(self, tasks: list[CreateBotDeliveryTask]) -> None:
        """
        Persist a **batch** of task inside the **current transaction.

        If a task with the same (outbox_id, subscription_id) already exists,
        it will not be inserted again.
        """
        with start_span(op="db", name="store_delivery_tasks") as span:
            span.set_tag("tasks_count", len(tasks))

            for task in tasks:
                stmt = (
                    pg_insert(BotDeliveryTask)
                    .values(
                        outbox_id=task.outbox_id,
                        subscription_id=task.subscription_id,
                    )
                    .on_conflict_do_nothing(
                        constraint=constraints.bot_delivery_task_unique
                    )
                )
                await self._session.execute(stmt)

    async def mark_published(self, task_id: UUID) -> None:
        with start_span(op="db", name="mark_bot_delivery_task_published") as span:
            span.set_tag("task.id", str(task_id))

            stmt = (
                update(BotDeliveryTask)
                .where(BotDeliveryTask.id == task_id)
                .values(
                    published=True,
                    attempts=BotDeliveryTask.attempts + 1,
                    published_at=now_utc(),
                )
            )
            await self._session.execute(stmt)

    async def mark_failed(self, next_attempt_at: datetime, *, task_id: UUID) -> None:
        """
        Marks the specified task as failed.
        Increments the `attempts` counter for the task identified by `task_id`.
        """
        with start_span(op="db", name="mark_bot_delivery_task_failed") as span:
            span.set_tag("task.id", str(task_id))

            stmt = (
                update(BotDeliveryTask)
                .where(BotDeliveryTask.id == task_id)
                .values(
                    attempts=BotDeliveryTask.attempts + 1,
                    next_attempt_at=next_attempt_at,
                )
            )
            await self._session.execute(stmt)


class PgBotDeliveryTaskTxRepository(PgBotDeliveryTaskRepository):
    async def claim_batch(
        self, batch: int, *, max_attempts: int
    ) -> list[BotDeliveryTaskDTO]:
        """
        Claims a batch of unpublished delivery tasks.

        This method selects up to `batch` unpublished tasks from the database,
        locking them for update and skipping any that are already locked by other transactions.
        """
        with start_span(op="db", name="claim_delivery_tasks") as span:
            stmt = (
                select(BotDeliveryTask)
                .where(
                    BotDeliveryTask.published.is_(False),
                    BotDeliveryTask.attempts < max_attempts,
                    BotDeliveryTask.next_attempt_at <= now_utc(),
                )
                .with_for_update(skip_locked=True)
                .limit(batch)
            )

            rows = await self._session.scalars(stmt)

            result = [
                BotDeliveryTaskDTO(
                    id=row.id,
                    outbox_id=row.outbox_id,
                    subscription_id=row.subscription_id,
                    attempts=row.attempts,
                )
                for row in rows
            ]

            span.set_tag("claimed_count", len(result))

            return result

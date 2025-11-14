import traceback
from datetime import timedelta
from logging import Logger

from app.domains.engine import EngineDead, EngineRestored, EngineUpdated
from app.infra.database.uow import PgOutboxUnitOfWorkContext, PgUnitOfWork
from app.infra.utils.time import now_utc
from app.schemas.outbox import (
    OutboxDTO,
)
from app.services.fanout import BotTaskFanoutPlanner


class OutboxService:
    def __init__(
        self,
        uow: PgUnitOfWork[PgOutboxUnitOfWorkContext],
        fanout_planner: BotTaskFanoutPlanner,
        *,
        logger: Logger,
        batch=200,
        max_publish_attempts=5,
    ) -> None:
        self._uow = uow
        self._fanout_planner = fanout_planner

        self._logger = logger
        self._batch = batch
        self._max_attempts = max_publish_attempts

    async def process_outbox_batch(self) -> int:
        async with self._uow.begin() as uow:
            records = await uow.outbox.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )

            if not records:
                return 0

            self._logger.info(f"Processing outbox batch with {len(records)} records...")

            unhandled: list[OutboxDTO] = []
            engine_delivery_tasks = []
            for rec in records:
                match rec.event:
                    case EngineDead() | EngineRestored() | EngineUpdated():
                        engine_delivery_tasks.append(rec)
                    case _:
                        unhandled.append(rec)

            try:
                await self._fanout_planner.spawn_engine_delivery_tasks(
                    engine_delivery_tasks, ctx=uow
                )
                await self._mark_fanned_out(engine_delivery_tasks, uow=uow)
            except Exception:
                self._logger.error(
                    f"Error spawning engine delivery tasks: {traceback.format_exc()}"
                )
                await self._mark_failed(engine_delivery_tasks, uow=uow)

            if len(engine_delivery_tasks) != len(records):
                raise NotImplementedError(
                    f"Unhandled event types found: {', '.join(rec.event.name for rec in unhandled)}"
                )

            self._logger.info(f"Processed outbox batch with {len(records)} records")

            return len(records)

    async def _mark_failed(
        self, record: list[OutboxDTO], *, uow: PgOutboxUnitOfWorkContext
    ):
        for rec in record:
            next_attempt_at = now_utc() + timedelta(seconds=(rec.attempts + 1) ** 2)
            await uow.outbox.mark_failed(next_attempt_at, outbox_id=rec.id)

    async def _mark_fanned_out(
        self, record: list[OutboxDTO], *, uow: PgOutboxUnitOfWorkContext
    ):
        for rec in record:
            await uow.outbox.mark_fanned_out(rec.id)

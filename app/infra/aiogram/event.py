import asyncio
import traceback
from collections import Counter
from logging import Logger

from sentry_sdk import start_span

from aiogram import Bot
from app.infra.aiogram import text
from app.schemas.outbox import PublishBotDeliveryTask


class AiogramEventPublisher:
    def __init__(self, bot: Bot, *, logger: Logger):
        self._bot = bot
        self._logger = logger

    async def publish_batch(self, tasks: list[PublishBotDeliveryTask]) -> list[bool]:
        with start_span(op="task", name="publish_events_batch") as span:
            span.set_tag("tasks_count", len(tasks))
            atasks = []

            for task in tasks:
                atasks.append(asyncio.create_task(self._publish(task)))

            results = await asyncio.gather(*atasks)
            span.set_tag("success_count", Counter(results).get(True, 0))

            return results

    async def _publish(self, task: PublishBotDeliveryTask) -> bool:
        try:
            await self._bot.send_message(
                chat_id=task.telegram_id, text=text.from_event(task.event)
            )
            return True
        except Exception:
            self._logger.error(f"Failed to publish event: {traceback.format_exc()}")
            return False

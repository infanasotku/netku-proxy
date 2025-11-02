from aiogram import Bot
from app.schemas.outbox import OutboxDTO


class AiogramEventPublisher:
    def __init__(self, bot: Bot):
        self._bot = bot

    async def publish_batch(self, record: OutboxDTO):
        pass

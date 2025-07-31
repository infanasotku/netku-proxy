from faststream.rabbit import RabbitBroker, RabbitQueue

from app.schemas.outbox import OutboxDTO


class RabbitPublisher:
    def __init__(self, broker: RabbitBroker, *, queue: RabbitQueue):
        self._broker = broker
        self._queue = queue

    async def publish(self, dto: OutboxDTO, *, timeout: int | None = None) -> None:
        await self._broker.publish(
            dto.event.to_dict(),
            queue=self._queue,
            message_id=dto.id.hex,
            correlation_id=dto.caused_by,
            message_type=dto.event.name,
            content_type="application/json",
            timeout=timeout,
        )

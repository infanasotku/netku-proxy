from faststream.rabbit import RabbitBroker, RabbitQueue

from app.domains.event import DomainEvent


class RabbitPublisher:
    def __init__(self, broker: RabbitBroker, *, queue: RabbitQueue):
        self._broker = broker
        self._queue = queue

    async def publish(self, event: DomainEvent) -> None:
        await self._broker.publish(event.to_dict(), queue=self._queue)

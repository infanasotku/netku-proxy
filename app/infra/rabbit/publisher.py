import asyncio

from faststream.rabbit import RabbitBroker, RabbitQueue
from sentry_sdk import start_span
from sentry_sdk.tracing import Span

from app.schemas.outbox import OutboxDTO, OutboxPublishResult


class RabbitPublisher:
    def __init__(self, broker: RabbitBroker, *, queue: RabbitQueue):
        self._broker = broker
        self._queue = queue

    async def publish_batch(
        self, dtos: list[OutboxDTO], *, timeout: int | None = None
    ) -> list[OutboxPublishResult]:
        with start_span(op="queue.submit", name="Publish outbox batch") as span:
            span.set_tag("outbox.count", len(dtos))

            return await asyncio.gather(
                *(self._publish(dto, span=span, timeout=timeout) for dto in dtos)
            )

    async def _publish(
        self, dto: OutboxDTO, *, span: Span, timeout: int | None = None
    ) -> OutboxPublishResult:
        with span.start_child(op="queue.submit", name="Publish outbox message") as span:
            span.set_tag("outbox.id", dto.id.hex)
            span.set_tag("outbox.event", dto.event.name)
            try:
                await self._broker.publish(
                    dto.event.to_dict(),
                    queue=self._queue,
                    message_id=dto.id.hex,
                    correlation_id=dto.caused_by,
                    message_type=dto.event.name,
                    content_type="application/json",
                    timeout=timeout,
                )
            except Exception as e:
                span.set_tag("outbox.error", str(e))
                return OutboxPublishResult(
                    record=dto,
                    success=False,
                    error=str(e),
                )
            return OutboxPublishResult(
                record=dto,
                success=True,
                error=None,
            )

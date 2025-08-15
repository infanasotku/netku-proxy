import asyncio
from logging import Logger

from faststream.rabbit.publisher.asyncapi import AsyncAPIPublisher
from sentry_sdk import start_span
from sentry_sdk.tracing import Span

from app.schemas.outbox import OutboxDTO, OutboxPublishResult
from app.infra.utils.retry import retry


class RabbitOutboxPublisher:
    def __init__(self, publisher: AsyncAPIPublisher, *, logger: Logger | None = None):
        self._publisher = publisher
        self._logger = logger

    def _log(self, msg: str):
        if self._logger is not None:
            self._logger.debug(msg)

    async def publish_batch(
        self, dtos: list[OutboxDTO], *, timeout: int | None = None
    ) -> list[OutboxPublishResult]:
        with start_span(op="queue.submit", name="Publish outbox batch") as span:
            span.set_tag("outbox.count", len(dtos))

            return await asyncio.gather(
                *(self._publish(dto, parent_span=span, timeout=timeout) for dto in dtos)
            )

    async def _publish(
        self, dto: OutboxDTO, *, parent_span: Span, timeout: int | None = None
    ):
        with parent_span.start_child(
            op="queue.submit", name="Publish outbox message"
        ) as span:
            span.set_tag("outbox.id", dto.id.hex)
            span.set_tag("outbox.event", dto.event.name)

            @retry()
            async def _publish():
                await self._publisher.publish(
                    dto.event.to_dict(),
                    message_id=dto.id.hex,
                    correlation_id=dto.caused_by,
                    message_type=dto.event.name,
                    timeout=timeout,
                )

            try:
                await _publish()
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

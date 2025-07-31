from app.infra.database.uow import PostgresOutboxUnitOfWork
from app.infra.rabbit.publisher import RabbitPublisher
from app.schemas.outbox import OutboxPublishResult


class OutboxService:
    def __init__(
        self,
        uow: PostgresOutboxUnitOfWork,
        publisher: RabbitPublisher,
        *,
        batch=200,
        max_publish_attempts=5,
    ) -> None:
        self._uow = uow
        self._publisher = publisher
        self._batch = batch
        self._max_attempts = max_publish_attempts

    async def process_batch(self) -> list[OutboxPublishResult]:
        """
        Processes a batch of outbox records by claiming, publishing, and updating their status.

        Workflow
        --------
        - Claims a batch of outbox records that have not exceeded the maximum number of attempts.
        - Publishes each record using the configured publisher.
        - Marks records as sent if publishing succeeds, or as failed if an exception occurs.
        - Collects and returns the result for each record.

        Returns:
            A list of results for each processed outbox record, indicating
            success or failure, error message if any, and the number of attempts.
        """
        result = []
        async with self._uow.begin() as uow:
            records = await uow.outbox.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )
            if not records:
                return []

            for record in records:
                try:
                    await self._publisher.publish(record)
                except Exception as e:
                    await self._uow.outbox.mark_failed(record.id)
                    result.append(
                        OutboxPublishResult(
                            id=record.id,
                            success=False,
                            error=str(e),
                            attempts=record.attempts + 1,
                        )
                    )
                else:
                    await self._uow.outbox.mark_sent(record.id)
                    result.append(
                        OutboxPublishResult(
                            id=record.id,
                            success=True,
                            error=None,
                            attempts=1,
                        )
                    )

        return result

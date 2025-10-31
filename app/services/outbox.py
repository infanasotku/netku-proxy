from app.infra.database.uow import PgOutboxUnitOfWorkContext, PgUnitOfWork
from app.infra.rabbit.publisher import RabbitOutboxPublisher
from app.schemas.outbox import OutboxProcessingResult


class OutboxService:
    def __init__(
        self,
        uow: PgUnitOfWork[PgOutboxUnitOfWorkContext],
        publisher: RabbitOutboxPublisher,
        *,
        batch=200,
        max_publish_attempts=5,
    ) -> None:
        self._uow = uow
        self._publisher = publisher
        self._batch = batch
        self._max_attempts = max_publish_attempts

    async def process_batch(self) -> list[OutboxProcessingResult]:
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
        async with self._uow.begin() as uow:
            records = await uow.outbox.claim_batch(
                self._batch, max_attempts=self._max_attempts
            )
            if not records:
                return []

            results = []
            publish_results = await self._publisher.publish_batch(records)
            for res in publish_results:
                if res.success:
                    await uow.outbox.mark_sent(res.record.id)
                else:
                    await uow.outbox.mark_failed(res.record.id)
                results.append(
                    OutboxProcessingResult(
                        record=res.record,
                        success=res.success,
                        error=res.error,
                        attempts=res.record.attempts + 1,
                    )
                )

            return results

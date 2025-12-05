from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.infra.database.repositories.outbox import (
    PgOutboxRepository,
    PgOutboxTxRepository,
)
from app.infra.database.repositories.tasks import (
    PgBotDeliveryTaskRepository,
    PgBotDeliveryTaskTxRepository,
)
from app.infra.database.uows.base import PgTxUOWContext, PgUnitOfWork, PgUOWContext


class PgTaskUOWContext(PgUOWContext):
    def __init__(self, *, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.tasks = PgBotDeliveryTaskRepository(session)


class PgTaskTxUOWContext(PgTxUOWContext):
    def __init__(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> None:
        super().__init__(session=session, transaction=transaction)
        self.tasks = PgBotDeliveryTaskTxRepository(session)


class PgOutboxUOWContext(PgUOWContext):
    def __init__(self, *, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.outbox = PgOutboxRepository(session)


class PgOutboxTxUOWContext(PgTxUOWContext):
    def __init__(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> None:
        super().__init__(session=session, transaction=transaction)
        self.outbox = PgOutboxTxRepository(session)


class PgFullOutboxUOWContext(PgTaskUOWContext, PgOutboxUOWContext):
    def __init__(self, *, session: AsyncSession) -> None:
        super().__init__(session=session)


class PgFullOutboxTxUOWContext(PgTaskTxUOWContext, PgOutboxTxUOWContext):
    def __init__(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> None:
        super().__init__(session=session, transaction=transaction)


class PgOutboxUnitOfWork(
    PgUnitOfWork[PgFullOutboxUOWContext, PgFullOutboxTxUOWContext]
):
    def _make_tx_ctx(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> PgFullOutboxTxUOWContext:
        return PgFullOutboxTxUOWContext(session=session, transaction=transaction)

    def _make_plain_ctx(self, *, session: AsyncSession) -> PgFullOutboxUOWContext:
        return PgFullOutboxUOWContext(session=session)

from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.infra.database.repositories.subscription import (
    PgSubscriptionRepository,
    PgSubscriptionTxRepository,
)
from app.infra.database.uows.base import PgTxUOWContext, PgUnitOfWork, PgUOWContext


class PgSubscriptionUOWContext(PgUOWContext):
    def __init__(self, *, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.tasks = PgSubscriptionRepository(session)


class PgSubscriptionTxUOWContext(PgTxUOWContext):
    def __init__(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> None:
        super().__init__(session=session, transaction=transaction)
        self.tasks = PgSubscriptionTxRepository(session)


class PgBillingUnitOfWork(
    PgUnitOfWork[PgSubscriptionUOWContext, PgSubscriptionTxUOWContext]
):
    def _make_tx_ctx(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> PgSubscriptionTxUOWContext:
        return PgSubscriptionTxUOWContext(session=session, transaction=transaction)

    def _make_plain_ctx(self, *, session: AsyncSession) -> PgSubscriptionUOWContext:
        return PgSubscriptionUOWContext(session=session)

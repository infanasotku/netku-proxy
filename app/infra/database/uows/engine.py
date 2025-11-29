from sqlalchemy.ext.asyncio import AsyncSession, AsyncSessionTransaction

from app.infra.database.repositories.engine import (
    PgEngineRepository,
    PgEngineTxRepository,
)
from app.infra.database.uows.base import PgUnitOfWork
from app.infra.database.uows.outbox import PgOutboxTxUOWContext, PgOutboxUOWContext


class PgEngineUOWContext(PgOutboxUOWContext):
    def __init__(self, *, session: AsyncSession) -> None:
        super().__init__(session=session)
        self.engine = PgEngineRepository(session)


class PgEngineTxUOWContext(PgOutboxTxUOWContext):
    def __init__(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> None:
        super().__init__(session=session, transaction=transaction)
        self.engine = PgEngineTxRepository(session)


class PgEngineUnitOfWork(PgUnitOfWork[PgEngineUOWContext, PgEngineTxUOWContext]):
    def _make_tx_ctx(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> PgEngineTxUOWContext:
        return PgEngineTxUOWContext(session=session, transaction=transaction)

    def _make_plain_ctx(self, *, session: AsyncSession) -> PgEngineUOWContext:
        return PgEngineUOWContext(session=session)

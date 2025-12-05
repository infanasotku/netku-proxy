import asyncio
from abc import ABC, abstractmethod
from contextlib import asynccontextmanager
from typing import (
    AsyncContextManager,
    AsyncIterator,
    Generic,
    Literal,
    TypeVar,
    overload,
)

from sentry_sdk import start_span
from sqlalchemy.ext.asyncio import (
    AsyncSession,
    AsyncSessionTransaction,
    async_sessionmaker,
)


class PgUOWContext:
    def __init__(self, *, session: AsyncSession):
        self._session = session


class PgTxUOWContext(PgUOWContext):
    def __init__(self, *, session: AsyncSession, transaction: AsyncSessionTransaction):
        super().__init__(session=session)
        self._transaction = transaction


PlainContextT = TypeVar(
    "PlainContextT", bound=PgUOWContext, covariant=True
)  # TransactionLessContextT
TxContextT = TypeVar(
    "TxContextT", bound=PgTxUOWContext, covariant=True
)  # TransactionFullContextT


class PgUnitOfWork(ABC, Generic[PlainContextT, TxContextT]):
    def __init__(
        self,
        *,
        plain_sessionmaker: async_sessionmaker[AsyncSession],
        tx_sessionmaker: async_sessionmaker[AsyncSession],
    ) -> None:
        self._plain_sessionmaker = plain_sessionmaker
        self._tx_sessionmaker = tx_sessionmaker

    @abstractmethod
    def _make_tx_ctx(
        self, *, session: AsyncSession, transaction: AsyncSessionTransaction
    ) -> TxContextT: ...
    @abstractmethod
    def _make_plain_ctx(self, *, session: AsyncSession) -> PlainContextT: ...

    @overload
    async def _start(self, *, with_tx: Literal[True]) -> TxContextT: ...
    @overload
    async def _start(self, *, with_tx: Literal[False]) -> PlainContextT: ...
    async def _start(self, *, with_tx: bool) -> TxContextT | PlainContextT:
        if with_tx:
            session = self._tx_sessionmaker()
            transatcion = await session.begin()
            return self._make_tx_ctx(session=session, transaction=transatcion)
        else:
            session = self._plain_sessionmaker()
            return self._make_plain_ctx(session=session)

    async def _finish(
        self,
        exc: BaseException | None,
        *,
        ctx: TxContextT | PlainContextT,
    ):
        try:
            if exc is None:
                if isinstance(ctx, PgTxUOWContext):
                    await ctx._transaction.commit()
            else:
                raise exc
        except BaseException:
            if isinstance(ctx, PgTxUOWContext):
                try:
                    await ctx._session.rollback()
                except Exception:
                    pass
            raise
        finally:
            await ctx._session.close()

    @overload
    def begin(self, *, with_tx: Literal[True]) -> AsyncContextManager[TxContextT]: ...
    @overload
    def begin(
        self, *, with_tx: Literal[False]
    ) -> AsyncContextManager[PlainContextT]: ...
    @asynccontextmanager
    async def begin(
        self, *, with_tx: bool
    ) -> AsyncIterator[TxContextT | PlainContextT]:
        tr_name = "uow_with_transaction" if with_tx else "uow"
        with start_span(op="db", name=tr_name):
            ctx = await self._start(with_tx=with_tx)
            try:
                yield ctx
            except BaseException as ex:  # With CancelledError
                await asyncio.shield(self._finish(ex, ctx=ctx))
            else:
                await asyncio.shield(self._finish(None, ctx=ctx))

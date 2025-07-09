from typing import TypeAlias, Annotated, AsyncContextManager, Callable
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import UniqueConstraint, Enum
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, BIGINT
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.engine import EngineStatus


uuidpk = Annotated[
    UUID, mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
]
GetSQLDB: TypeAlias = Callable[[], AsyncContextManager[AsyncSession]]


class Base(DeclarativeBase):
    id: Mapped[uuidpk]


class Engine(Base):
    __tablename__ = "engines"

    uuid: Mapped[UUID] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    created: Mapped[datetime] = mapped_column(nullable=False)
    status: Mapped[EngineStatus] = mapped_column(Enum(EngineStatus), nullable=False)
    addr: Mapped[str] = mapped_column(nullable=False)

    # Version
    version_timestamp: Mapped[int] = mapped_column(BIGINT, nullable=False)
    version_seq: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (UniqueConstraint("version_timestamp", "version_seq"),)

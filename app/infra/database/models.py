from datetime import datetime
from typing import Annotated
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
)
from sqlalchemy.dialects.postgresql import BIGINT, JSONB
from sqlalchemy.dialects.postgresql import UUID as SQLUUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from app.domains.engine import EngineStatus
from app.infra.database import constraints
from app.infra.utils.time import now_utc

uuidpk = Annotated[
    UUID, mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
]


class Base(DeclarativeBase):
    id: Mapped[uuidpk]


class Engine(Base):
    """
    Represents an engine metadata in the database.

    Attributes:
        uuid: Optional unique access key for the engine.
        created: Timestamp indicating when the engine record was created by engine itself.
        status: Current status of the engine.
        addr: Address associated with the engine.
        version_timestamp: High-order **timestamp** component of the aggregate version.
        version_seq: Low-order **sequence** component of the aggregate version.

    Table Constraints
    -----------------
    - UniqueConstraint on ('version_timestamp', 'version_seq')
    """

    __tablename__ = "engines"

    uuid: Mapped[UUID | None] = mapped_column(SQLUUID(as_uuid=True), nullable=True)
    created: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    status: Mapped[EngineStatus] = mapped_column(Enum(EngineStatus), nullable=False)
    addr: Mapped[str] = mapped_column(nullable=False)

    # Version
    version_timestamp: Mapped[int] = mapped_column(BIGINT, nullable=False)
    version_seq: Mapped[int] = mapped_column(nullable=False)

    subscriptions: Mapped[list["EngineSubscription"]] = relationship(
        back_populates="engine"
    )

    __table_args__ = (constraints.engine_version_unique,)

    def __str__(self) -> str:
        return f"{self.id}_{self.addr}_{self.status}"


class Outbox(Base):
    """
    Canonical transactional-outbox event.

    Attributes:
        id: Stable identifier (e.g. incoming event id or UUID5).
        caused_by: Correlation token such as HTTP request id or stream id.
            This is meta information used for tracing.
        body: Serialized payload describing what should be delivered.
        fanned_out: Flag flipped to TRUE after the fan-out worker
            successfully materialises all delivery tasks for this record.
        created_at: Timestamp when the outbox record was inserted.
        fanned_out_at: Timestamp when fan-out finished, else None.
        attempts: Number of fan-out attempts performed so far.
        next_attempt_at: When the next fan-out attempt is allowed.

    Indexes
    -------
    - `caused_by` b-tree for auditing and deduplication checks.
    - Partial index `ix_outbox_pending` on `fanned_out = FALSE` ordered by
      `next_attempt_at` to feed the fan-out worker efficiently.
    """

    __tablename__ = "outbox"

    caused_by: Mapped[str] = mapped_column(
        nullable=False,
        index=True,  # Look-ups by correlation key
    )

    body: Mapped[dict] = mapped_column(
        JSONB,
        nullable=False,
    )

    fanned_out: Mapped[bool] = mapped_column(
        nullable=False,
        default=False,
    )
    attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    fanned_out_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    __table_args__ = (
        # Fast batch pick-up for relay workers
        Index(
            "ix_outbox_pending",
            "next_attempt_at",
            postgresql_where=(
                Column("fanned_out", Boolean).is_(False)
            ),  # Partial index
        ),
    )


class User(Base):
    """Telegram end user that can subscribe to engine events."""

    __tablename__ = "users"

    telegram_id: Mapped[str] = mapped_column(nullable=False, unique=True)
    description: Mapped[str] = mapped_column(nullable=True)

    subscriptions: Mapped[list["EngineSubscription"]] = relationship(
        back_populates="user"
    )

    def __str__(self) -> str:
        return self.description


class EngineSubscription(Base):
    """Link table that records which users want updates from which engine."""

    __tablename__ = "engine_subscriptions"

    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    user: Mapped[User] = relationship(
        foreign_keys=[user_id], back_populates="subscriptions"
    )
    engine_id: Mapped[UUID] = mapped_column(ForeignKey("engines.id"), nullable=False)
    engine: Mapped[Engine] = relationship(
        foreign_keys=[engine_id], back_populates="subscriptions"
    )

    event: Mapped[str]

    def __str__(self) -> str:
        return f"{self.event}_{self.user_id}_{self.engine_id}"


class BotDeliveryTask(Base):
    """
    Fan-out unit representing a pending delivery.

    Each row ties an `Outbox` record to a subscriber (via engine subscription),
    stores the rendered message, and tracks whether the bot has published it.
    """

    __tablename__ = "delivery_tasks"

    outbox_id: Mapped[UUID] = mapped_column(
        ForeignKey("outbox.id", ondelete="CASCADE"), nullable=False
    )
    subscription_id: Mapped[UUID] = mapped_column(
        ForeignKey("engine_subscriptions.id"), nullable=False
    )

    published: Mapped[bool] = mapped_column(nullable=False, default=False)
    attempts: Mapped[int] = mapped_column(
        nullable=False,
        default=0,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    next_attempt_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=now_utc,
    )

    __table_args__ = (
        # Fast batch pick-up for relay workers
        Index(
            "ix_delivery_task_pending",
            "next_attempt_at",
            postgresql_where=(Column("published", Boolean).is_(False)),  # Partial index
        ),
        constraints.bot_delivery_task_unique,
    )

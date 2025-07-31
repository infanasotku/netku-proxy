from typing import Annotated
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Boolean, Column, Index, UniqueConstraint, Enum, DateTime
from sqlalchemy.orm import mapped_column, Mapped, DeclarativeBase
from sqlalchemy.dialects.postgresql import UUID as SQLUUID, BIGINT, JSONB

from app.domains.engine import EngineStatus


uuidpk = Annotated[
    UUID, mapped_column(SQLUUID(as_uuid=True), primary_key=True, default=uuid4)
]


class Base(DeclarativeBase):
    id: Mapped[uuidpk]


class Engine(Base):
    """
    Represents an engine metadata in the database.

    Attributes:
        uuid (UUID | None): Optional unique access key for the engine.
        created (datetime): Timestamp indicating when the engine record was created by engine itself.
        status (EngineStatus): Current status of the engine.
        addr (str): Address associated with the engine.
        version_timestamp (int): High-order **timestamp** component of the aggregate version.
        version_seq (int): Low-order **sequence** component of the aggregate version.

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

    __table_args__ = (UniqueConstraint("version_timestamp", "version_seq"),)


class OutboxRecord(Base):
    """
    Transactional-outbox row.

    Each row is written **inside the same database transaction** that modifies
    your domain state.
    A relay process later reads unpublished rows and pushes them to a broker.

    Attributes:
        id (UUID): Deterministic message_id (e.g. event_id or UUID5(caused_by:event)).
        caused_by (str): Correlation key such as Redis stream_id or HTTP request_id.
        body (dict): Result of event.to_dict(); contains event_type, aggregate_id, etc.
        published (bool): Set to TRUE by the relay after a successful broker publish.
        created_at (datetime): Timestamp when the outbox record was created.
        published_at (datetime | None): Timestamp when the record was published, or None if unpublished.
        attempts (int): Number of publish attempts for this outbox record.

    Table Indexes
    -----------------
    - Index on 'caused_by' for fast correlation lookups.
    - Partial index 'ix_outbox_unpublished' on 'published' = FALSE for efficient relay worker pick-up.
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

    published: Mapped[bool] = mapped_column(
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
        default=datetime.now,
    )
    published_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    __table_args__ = (
        # Fast batch pick-up for relay workers
        Index(
            "ix_outbox_unpublished",
            "published",
            postgresql_where=(Column("published", Boolean).is_(False)),  # Partial index
        ),
    )

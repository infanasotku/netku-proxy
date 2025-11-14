"""Add delivery task and it dependencies

Revision ID: 97e038ee95bb
Revises: a66e839a709a
Create Date: 2025-11-02 23:37:52.849632

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "97e038ee95bb"
down_revision: Union[str, Sequence[str], None] = "a66e839a709a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "users",
        sa.Column("telegram_id", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_table(
        "engine_subscriptions",
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("engine_id", sa.UUID(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["engine_id"],
            ["engines.id"],
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "bot_delivery_tasks",
        sa.Column("outbox_id", sa.UUID(), nullable=False),
        sa.Column("subscription_id", sa.UUID(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(
            ["outbox_id"],
            ["outbox.id"],
        ),
        sa.ForeignKeyConstraint(
            ["subscription_id"],
            ["engine_subscriptions.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_bot_delivery_task_pending",
        "bot_delivery_tasks",
        ["published"],
        unique=False,
        postgresql_where=sa.text("published IS false"),
    )
    op.add_column("outbox", sa.Column("fanned_out", sa.Boolean(), nullable=False))
    op.add_column(
        "outbox", sa.Column("fanned_out_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column(
        "outbox",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_index(
        op.f("ix_outbox_unpublished"),
        table_name="outbox",
        postgresql_where="(published IS FALSE)",
    )
    op.create_index(
        "ix_outbox_pending",
        "outbox",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("fanned_out IS false"),
    )
    op.drop_column("outbox", "published")
    op.drop_column("outbox", "published_at")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "outbox",
        sa.Column(
            "published_at",
            postgresql.TIMESTAMP(timezone=True),
            autoincrement=False,
            nullable=True,
        ),
    )
    op.add_column(
        "outbox",
        sa.Column("published", sa.BOOLEAN(), autoincrement=False, nullable=False),
    )
    op.drop_index(
        "ix_outbox_pending",
        table_name="outbox",
        postgresql_where=sa.text("fanned_out IS false"),
    )
    op.create_index(
        op.f("ix_outbox_unpublished"),
        "outbox",
        ["published"],
        unique=False,
        postgresql_where="(published IS FALSE)",
    )
    op.drop_column("outbox", "next_attempt_at")
    op.drop_column("outbox", "fanned_out_at")
    op.drop_column("outbox", "fanned_out")
    op.drop_index(
        "ix_bot_delivery_task_pending",
        table_name="bot_delivery_tasks",
        postgresql_where=sa.text("published IS false"),
    )
    op.drop_table("bot_delivery_tasks")
    op.drop_table("engine_subscriptions")
    op.drop_table("users")

"""Add attempts to delivery_tasks

Revision ID: 91c2ff7519d4
Revises: 97e038ee95bb
Create Date: 2025-11-03 01:10:33.981091

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "91c2ff7519d4"
down_revision: Union[str, Sequence[str], None] = "97e038ee95bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "bot_delivery_tasks", sa.Column("attempts", sa.Integer(), nullable=False)
    )
    op.add_column(
        "bot_delivery_tasks",
        sa.Column("next_attempt_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.drop_index(
        op.f("ix_bot_delivery_task_pending"),
        table_name="bot_delivery_tasks",
        postgresql_where="(published IS FALSE)",
    )
    op.create_index(
        "ix_bot_delivery_task_pending",
        "bot_delivery_tasks",
        ["next_attempt_at"],
        unique=False,
        postgresql_where=sa.text("published IS false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_bot_delivery_task_pending",
        table_name="bot_delivery_tasks",
        postgresql_where=sa.text("published IS false"),
    )
    op.create_index(
        op.f("ix_bot_delivery_task_pending"),
        "bot_delivery_tasks",
        ["published"],
        unique=False,
        postgresql_where="(published IS FALSE)",
    )
    op.drop_column("bot_delivery_tasks", "next_attempt_at")
    op.drop_column("bot_delivery_tasks", "attempts")

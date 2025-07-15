"""Add outbox table

Revision ID: 0804875c91bb
Revises: d76351334e79
Create Date: 2025-07-10 17:47:45.855652

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "0804875c91bb"
down_revision: Union[str, Sequence[str], None] = "d76351334e79"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "outbox",
        sa.Column("caused_by", sa.String(), nullable=False),
        sa.Column("body", postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column("published", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("published_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_outbox_caused_by"), "outbox", ["caused_by"], unique=False)
    op.create_index(
        "ix_outbox_unpublished",
        "outbox",
        ["published"],
        unique=False,
        postgresql_where=sa.text("published IS false"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(
        "ix_outbox_unpublished",
        table_name="outbox",
        postgresql_where=sa.text("published IS false"),
    )
    op.drop_index(op.f("ix_outbox_caused_by"), table_name="outbox")
    op.drop_table("outbox")

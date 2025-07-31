"""Add outbox attempts

Revision ID: a66e839a709a
Revises: 0804875c91bb
Create Date: 2025-07-31 09:56:29.541904

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "a66e839a709a"
down_revision: Union[str, Sequence[str], None] = "0804875c91bb"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column("outbox", sa.Column("attempts", sa.Integer(), nullable=True))
    op.execute("UPDATE outbox SET attempts = 0 WHERE attempts IS NULL")
    op.alter_column("outbox", "attempts", nullable=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column("outbox", "attempts")

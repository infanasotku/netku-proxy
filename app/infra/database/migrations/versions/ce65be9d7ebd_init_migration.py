"""Init migration

Revision ID: ce65be9d7ebd
Revises:
Create Date: 2025-07-09 23:00:48.631832

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "ce65be9d7ebd"
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "engines",
        sa.Column("uuid", sa.UUID(), nullable=True),
        sa.Column("created", sa.DateTime(), nullable=False),
        sa.Column(
            "status",
            sa.Enum("ACTIVE", "READY", "DEAD", name="enginestatus"),
            nullable=False,
        ),
        sa.Column("addr", sa.String(), nullable=False),
        sa.Column("version_timestamp", sa.BIGINT(), nullable=False),
        sa.Column("version_seq", sa.Integer(), nullable=False),
        sa.Column("id", sa.UUID(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version_timestamp", "version_seq"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("engines")

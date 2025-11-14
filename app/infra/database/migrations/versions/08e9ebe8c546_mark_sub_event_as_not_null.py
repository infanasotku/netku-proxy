"""Mark sub event as not null

Revision ID: 08e9ebe8c546
Revises: 3ee8129175d8
Create Date: 2025-11-14 23:37:08.359626

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "08e9ebe8c546"
down_revision: Union[str, Sequence[str], None] = "3ee8129175d8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        op.f("delivery_tasks_outbox_id_fkey"), "delivery_tasks", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("delivery_tasks_outbox_id_fkey"),
        "delivery_tasks",
        "outbox",
        ["outbox_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("delivery_tasks_outbox_id_fkey"), "delivery_tasks", type_="foreignkey"
    )
    op.create_foreign_key(
        op.f("delivery_tasks_outbox_id_fkey"),
        "delivery_tasks",
        "outbox",
        ["outbox_id"],
        ["id"],
    )

"""Add cascade for tasks and subscriptions

Revision ID: eb691ba21ad8
Revises: 08e9ebe8c546
Create Date: 2025-12-01 15:29:44.198875

"""

from typing import Sequence, Union

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "eb691ba21ad8"
down_revision: Union[str, Sequence[str], None] = "08e9ebe8c546"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.drop_constraint(
        op.f("delivery_tasks_subscription_id_fkey"),
        "delivery_tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("delivery_tasks_subscription_id_fkey"),
        "delivery_tasks",
        "engine_subscriptions",
        ["subscription_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        op.f("engine_subscriptions_user_id_fkey"),
        "engine_subscriptions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("engine_subscriptions_engine_id_fkey"),
        "engine_subscriptions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("engine_subscriptions_user_id_fkey"),
        "engine_subscriptions",
        "users",
        ["user_id"],
        ["id"],
        ondelete="CASCADE",
    )
    op.create_foreign_key(
        op.f("engine_subscriptions_engine_id_fkey"),
        "engine_subscriptions",
        "engines",
        ["engine_id"],
        ["id"],
        ondelete="CASCADE",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(
        op.f("engine_subscriptions_user_id_fkey"),
        "engine_subscriptions",
        type_="foreignkey",
    )
    op.drop_constraint(
        op.f("engine_subscriptions_engine_id_fkey"),
        "engine_subscriptions",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("engine_subscriptions_engine_id_fkey"),
        "engine_subscriptions",
        "engines",
        ["engine_id"],
        ["id"],
    )
    op.create_foreign_key(
        op.f("engine_subscriptions_user_id_fkey"),
        "engine_subscriptions",
        "users",
        ["user_id"],
        ["id"],
    )
    op.drop_constraint(
        op.f("delivery_tasks_subscription_id_fkey"),
        "delivery_tasks",
        type_="foreignkey",
    )
    op.create_foreign_key(
        op.f("delivery_tasks_subscription_id_fkey"),
        "delivery_tasks",
        "engine_subscriptions",
        ["subscription_id"],
        ["id"],
    )

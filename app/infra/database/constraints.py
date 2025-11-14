from sqlalchemy import UniqueConstraint

bot_delivery_task_unique = UniqueConstraint(
    "outbox_id",
    "subscription_id",
    name="uq_bot_delivery_task",
)

engine_version_unique = UniqueConstraint(
    "version_timestamp",
    "version_seq",
    name="uq_engine_version",
)

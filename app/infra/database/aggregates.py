from sqlalchemy import func, select
from sqlalchemy.orm import relationship

from app.infra.database.models import Base, Engine, EngineSubscription, User

subscription_agg = (
    select(
        EngineSubscription.user_id,
        EngineSubscription.engine_id,
        func.array_agg(EngineSubscription.event).label("events"),
        func.array_agg(EngineSubscription.id).label("subscription_ids"),
    ).group_by(EngineSubscription.user_id, EngineSubscription.engine_id)
).subquery()


class UserSubscriptionGroup(Base):
    __table__ = subscription_agg
    __mapper_args__ = {
        "primary_key": (
            subscription_agg.c.user_id,
            subscription_agg.c.engine_id,
        )
    }

    engine = relationship(
        Engine,
        primaryjoin=lambda: Engine.id == subscription_agg.c.engine_id,
        viewonly=True,
    )
    user = relationship(
        User,
        primaryjoin=lambda: User.id == subscription_agg.c.user_id,
        viewonly=True,
    )

from uuid import UUID

from sentry_sdk import start_span
from sqlalchemy import select

from app.domains.event import DomainEvent
from app.infra.database.models import EngineSubscription, User
from app.infra.database.repositories.base import PostgresRepository


class PgSubscriptionRepository(PostgresRepository):
    async def get_engine_subscriptions_for_events(
        self, events: list[DomainEvent]
    ) -> dict[str, list[UUID]]:
        with start_span(op="db", name="get_engine_subscriptions_for_events"):
            names = {event.name for event in events}

            stmt = select(EngineSubscription.id, EngineSubscription.event).where(
                EngineSubscription.event.in_(names)
            )
            rows = (await self._session.execute(stmt)).all()

            res = {}
            for id, event in rows:
                res.setdefault(event, []).append(id)

            return res

    async def get_telegram_ids_for_subscriptions(
        self, subscription_ids: list[UUID]
    ) -> list[str]:
        with start_span(op="db", name="get_telegram_ids_for_subscriptions"):
            stmt = (
                select(EngineSubscription.id, User.telegram_id)
                .join(User, EngineSubscription.user_id == User.id)
                .where(EngineSubscription.id.in_(subscription_ids))
            )
            rows = (await self._session.execute(stmt)).all()
            sub_telegram_ids_dict = {id: telegram_id for id, telegram_id in rows}

            return [sub_telegram_ids_dict[id] for id in subscription_ids]

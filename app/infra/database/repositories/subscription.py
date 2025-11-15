from uuid import UUID

from sentry_sdk import start_span
from sqlalchemy import select, tuple_

from app.domains.event import DomainEvent
from app.infra.database.models import EngineSubscription, User
from app.infra.database.repositories.base import PostgresRepository


class PgSubscriptionRepository(PostgresRepository):
    async def get_engine_subscriptions_for_events(
        self, events: list[DomainEvent]
    ) -> dict[DomainEvent, list[UUID]]:
        with start_span(op="db", name="get_engine_subscriptions_for_events"):
            names_ids = ((event.name, event.aggregate_id) for event in events)

            stmt = select(
                EngineSubscription.id,
                EngineSubscription.engine_id,
                EngineSubscription.event,
            ).where(
                tuple_(EngineSubscription.event, EngineSubscription.engine_id).in_(
                    names_ids
                )
            )
            rows = (await self._session.execute(stmt)).all()

            event_subsription_dict = {}
            for id, engine_id, event in rows:
                event_subsription_dict.setdefault((engine_id, event), []).append(id)

            return {
                event: event_subsription_dict.get((event.aggregate_id, event.name), [])
                for event in events
            }

    async def get_telegram_ids_for_subscriptions(
        self, subscription_ids: list[UUID]
    ) -> dict[UUID, str]:
        with start_span(op="db", name="get_telegram_ids_for_subscriptions"):
            stmt = (
                select(EngineSubscription.id, User.telegram_id)
                .join(User, EngineSubscription.user_id == User.id)
                .where(EngineSubscription.id.in_(subscription_ids))
            )
            rows = (await self._session.execute(stmt)).all()
            return {id: telegram_id for id, telegram_id in rows}

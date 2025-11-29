from uuid import UUID

from sentry_sdk import start_span
from sqlalchemy import delete, insert, select, tuple_

from app.domains.event import DomainEvent
from app.infra.database.models import EngineSubscription, User
from app.infra.database.repositories.base import PostgresRepository
from app.schemas.billing import CreateEngineSubscription, EngineSubscriptionDTO


def _to_dto(row: EngineSubscription) -> EngineSubscriptionDTO:
    return EngineSubscriptionDTO(
        id=row.id,
        engine_id=row.engine_id,
        user_id=row.user_id,
        event=row.event,
    )


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
        with start_span(op="db", name="get_telegram_ids_for_engine_subscriptions"):
            stmt = (
                select(EngineSubscription.id, User.telegram_id)
                .join(User, EngineSubscription.user_id == User.id)
                .where(EngineSubscription.id.in_(subscription_ids))
            )
            rows = (await self._session.execute(stmt)).all()
            return {id: telegram_id for id, telegram_id in rows}

    async def get_subscriptions_by_user_and_engine(
        self, user_id: UUID, engine_id: UUID
    ) -> list[EngineSubscriptionDTO]:
        with start_span(op="db", name="get_engine_subscriptions_by_user_and_engine"):
            stmt = select(EngineSubscription).where(
                EngineSubscription.user_id == user_id,
                EngineSubscription.engine_id == engine_id,
            )

            rows = await self._session.scalars(stmt)
            return [_to_dto(row) for row in rows]

    async def delete_subscriptions(self, subscription_ids: list[UUID]) -> None:
        with start_span(op="db", name="delete_engine_subscriptions"):
            stmt = delete(EngineSubscription).where(
                EngineSubscription.id.in_(subscription_ids)
            )
            await self._session.execute(stmt)

    async def insert_subscriptions(
        self, subscriptions: list[CreateEngineSubscription]
    ) -> None:
        with start_span(op="db", name="insert_engine_subscriptions"):
            stmt = insert(EngineSubscription).values(
                [sub.model_dump() for sub in subscriptions]
            )

            await self._session.execute(stmt)

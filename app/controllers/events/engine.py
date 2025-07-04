from faststream.redis import RedisRouter
from dependency_injector.wiring import inject, Provide
from pydantic import BaseModel

from app.infra.redis.streams import engine_stream
from app.contracts.services.proxy import ProxyService
from app.container import Container

router = RedisRouter()


class RedisKeyEvent(BaseModel):
    event: str
    key: str


@router.subscriber(stream=engine_stream)
async def handle_keyevents(key_event: RedisKeyEvent):
    match key_event.event:
        case "expired":
            await handle_engine_died(key_event.key)
        case "hset":
            await handle_engine_info_changed(key_event.key)


@inject
async def handle_engine_died(
    key: str, proxy_service: ProxyService = Provide[Container.proxy_service]
):
    print("died", key)


@inject
async def handle_engine_info_changed(
    key: str, proxy_service: ProxyService = Provide[Container.proxy_service]
):
    print("hset", key)

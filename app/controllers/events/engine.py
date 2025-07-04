from faststream.redis import RedisRouter
from pydantic import BaseModel

from app.infra.redis.streams import engine_stream

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


async def handle_engine_died(key: str):
    print("dead", key)


async def handle_engine_info_changed(key: str):
    print("hset", key)

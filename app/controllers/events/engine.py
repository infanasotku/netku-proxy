from logging import Logger
from typing import Awaitable, cast
from uuid import UUID

from faststream.exceptions import AckMessage
from faststream.redis import RedisRouter, RedisMessage
from dependency_injector.wiring import inject, Provide
from redis.asyncio import Redis
from pydantic import BaseModel

from app.infra.redis.streams import engine_stream
from app.contracts.services.proxy import EngineRemoveError, EngineService
from app.schemas.engine import EngineCmd
from app.container import Container

from app.domains.engine import Version

router = RedisRouter()


class RedisKeyEvent(BaseModel):
    event: str
    key: str


KEY_PREFIX = "xrayEngines:"


def _check_prefix(key: str, logger: Logger = Provide[Container.logger]):
    if KEY_PREFIX not in key:
        logger.warning(f"Received event from engine stream with invalid key: <{key}>.")
        raise AckMessage()


def _get_stream_id(message: RedisMessage) -> str:
    raw_message = getattr(message, "raw_message")
    return raw_message["message_ids"][0].decode()


def _get_outbox_id(message: RedisMessage):
    raw_message = getattr(message, "raw_message")
    stream_name: str = raw_message["channel"]
    message_id: str = _get_stream_id(message)
    return "{0}:{1}".format(stream_name, message_id)


@router.subscriber(stream=engine_stream, no_ack=True)
async def handle_keyevents(key_event: RedisKeyEvent, message: RedisMessage):
    _check_prefix(key_event.key)

    engine_key = key_event.key.removeprefix(KEY_PREFIX)
    stream_id = _get_stream_id(message)
    outbox_id = _get_outbox_id(message)
    version = Version.from_stream_id(stream_id)

    try:
        match key_event.event:
            case "expired":
                await handle_engine_dead(
                    engine_key=engine_key,
                    outbox_id=outbox_id,
                    version=version,
                )
            case "hset":
                await handle_engine_info_changed(
                    engine_key=engine_key,
                    outbox_id=outbox_id,
                    redis_key=key_event.key,
                    version=version,
                )
    except Exception:
        await message.nack()
    else:
        await message.ack()


@inject
async def handle_engine_dead(
    *,
    engine_key: str,
    outbox_id: str,
    version: Version,
    engine_service: EngineService = Provide[Container.engine_service],
    logger: Logger = Provide[Container.logger],
):
    try:
        await engine_service.remove(
            UUID(engine_key), caused_by=outbox_id, version=version
        )
    except EngineRemoveError as e:
        logger.warning(str(e))


@inject
async def handle_engine_info_changed(
    *,
    engine_key: str,
    outbox_id: str,
    version: Version,
    redis_key: str,
    redis: Redis = Provide[Container.redis],
    engine_service: EngineService = Provide[Container.engine_service],
):
    data: dict[bytes, bytes] = await cast(Awaitable, redis.hgetall(redis_key))
    payload = {k.decode(): data[k].decode() for k in data}
    payload["id"] = engine_key
    engine = EngineCmd.model_validate_strings(payload)

    await engine_service.upsert(engine, caused_by=outbox_id, version=version)

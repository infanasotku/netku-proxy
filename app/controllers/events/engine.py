from contextlib import asynccontextmanager
from logging import Logger
from typing import Awaitable, cast
from uuid import UUID
import asyncio

from faststream.exceptions import AckMessage
from faststream.redis import RedisRouter, RedisMessage
from faststream.redis.message import UnifyRedisMessage
from faststream.broker.message import AckStatus
from dependency_injector.wiring import inject, Provide
from redis.asyncio import Redis
from pydantic import BaseModel
from sentry_sdk import start_transaction

from app.infra.redis.streams import (
    engine_stream,
    dlq_stream,
    GROUP,
    CONSUMER,
    IDLE_MS,
    BATCH,
    PAUSE,
    MAX_RETRY,
)
from app.services.engine import EngineService
from app.services.exceptions.engine import EngineNotExistError
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
    stream_name: str = message.raw_message["channel"]
    message_id: str = _get_stream_id(message)
    return "{0}:{1}".format(stream_name, message_id)


@inject
def _get_logger(logger: Logger = Provide[Container.logger]):
    return logger


@router.subscriber(stream=engine_stream)
async def handle_keyevents(
    key_event: RedisKeyEvent,
    message: RedisMessage,
):
    _check_prefix(key_event.key)

    engine_key = key_event.key.removeprefix(KEY_PREFIX)
    stream_id = _get_stream_id(message)
    outbox_id = _get_outbox_id(message)
    version = Version.from_stream_id(stream_id)

    logger = _get_logger()

    tr_name = f"{key_event.event.upper()} engines/{'{engine_id}'}"
    with start_transaction(op="queue.task", name=tr_name) as tr:
        tr.set_tag("engine_key", engine_key)
        tr.set_tag("outbox_id", outbox_id)
        tr.set_tag("version", version.to_stream_id())

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
                case _:
                    logger.warning(f"Unknown event type: {key_event.event}")
        except Exception as e:
            logger.error(
                f"Error processing event [{key_event.event}] for engine [{engine_key}]  id [{stream_id}]: {e}",
                exc_info=True,
            )
            await message.nack()
        else:
            logger.info(
                f"Processed event [{key_event.event}] for engine [{engine_key}] id [{stream_id}]",
                extra=dict(channel=engine_stream.name),
            )


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
    except EngineNotExistError as e:
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
    logger: Logger = Provide[Container.logger],
):
    data: dict[bytes, bytes] = await cast(Awaitable, redis.hgetall(redis_key))
    if len(data) == 0:
        logger.warning(
            f"Engine with ID {engine_key} already removed, processing [info changed] event end."
        )

    payload = {k.decode(): data[k].decode() for k in data}
    payload["id"] = engine_key
    engine = EngineCmd.model_validate_strings(payload)

    await engine_service.upsert(engine, caused_by=outbox_id, version=version)


@asynccontextmanager
async def start_keyevents_reclaimer(redis: Redis, logger: Logger):
    async def _loop():
        cursor = "0-0"

        while True:
            cursor, entries = await redis.xautoclaim(
                engine_stream.name,
                groupname=GROUP,
                consumername=CONSUMER,
                min_idle_time=IDLE_MS,
                start_id=cursor,
                count=BATCH,
            )

            if len(entries) == 0:
                await asyncio.sleep(PAUSE)
                continue

            ids: list[bytes] = [id for id, _ in entries]
            ids_sorted = sorted(
                ids, key=lambda x: (int(x.split(b"-")[0]), int(x.split(b"-")[1]))
            )

            pendings = await redis.xpending_range(
                engine_stream.name,
                groupname=GROUP,
                min=ids_sorted[0],
                max=ids_sorted[-1],
                count=len(ids_sorted),
                consumername=CONSUMER,
            )
            deliveries_map: dict[bytes, int] = {
                msg["message_id"]: msg["times_delivered"] for msg in pendings
            }

            xacks = []

            for msg_id, raw in entries:
                deliveries = deliveries_map.get(msg_id, 1)

                if deliveries > MAX_RETRY:
                    raw[b"original_id"] = msg_id
                    await redis.xadd(dlq_stream.name, raw)  # Send message to DLQ
                    xacks.append(msg_id)
                    continue

                payload = {k.decode(): v.decode() for k, v in raw.items()}
                event = RedisKeyEvent(**payload)
                msg = UnifyRedisMessage(
                    raw_message=dict(
                        type="message", channel=engine_stream.name, data=raw
                    ),
                    body=raw,
                )
                cast(dict, msg.raw_message)["message_ids"] = [msg_id]

                try:
                    await handle_keyevents(event, msg)
                except Exception:  # Unhandled error
                    logger.error("Unhandled error in keyevents handler:", exc_info=True)
                    continue

                if msg.committed != AckStatus.nacked:
                    xacks.append(msg_id)

            if len(xacks) != 0:
                await redis.xack(engine_stream.name, GROUP, *xacks)

    async def _wrap():
        try:
            await _loop()
        except Exception:
            logger.critical(
                "Unhandled error occured in keyevents reclaimer:", exc_info=True
            )

    task = asyncio.create_task(_wrap())

    try:
        yield
    finally:
        task.cancel()

        try:
            await task  # Forward erros from task
        except asyncio.CancelledError:
            pass

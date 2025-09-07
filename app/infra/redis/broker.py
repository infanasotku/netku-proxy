from logging import Logger

from faststream.redis import RedisBroker


async def get_redis_broker(dsn: str, *, db: int = 0, logger: Logger | None = None):
    broker = RedisBroker(
        dsn,
        db=db,
        health_check_interval=10,
        retry_on_timeout=True,
        # Socket options
        socket_connect_timeout=5,
        socket_keepalive=True,
        logger=logger,
    )
    await broker.connect()
    try:
        yield broker
    finally:
        await broker.stop()


async def get_redis(broker: RedisBroker):
    return await broker.connect()

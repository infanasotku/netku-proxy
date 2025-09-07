from logging import Logger

from faststream.rabbit import RabbitBroker, utils


async def get_rabbit_broker(
    dsn: str, *, virtualhost: str | None = None, logger: Logger | None = None
):
    if virtualhost is not None and virtualhost.startswith("/"):
        virtualhost = "/" + virtualhost
    broker = RabbitBroker(
        dsn,
        virtualhost=virtualhost,
        publisher_confirms=True,
        # Heartbeat interval set to 20 seconds to balance timely detection of dead connections
        # and avoid excessive network traffic. This value helps maintain connection reliability
        # without causing unnecessary disconnects due to transient network issues.
        client_properties=utils.RabbitClientProperties(heartbeat=20),
        logger=logger,
    )
    await broker.connect()
    try:
        yield broker
    finally:
        await broker.stop()

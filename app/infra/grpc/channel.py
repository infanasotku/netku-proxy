from contextlib import asynccontextmanager
from logging import Logger
from typing import AsyncIterator, Protocol, AsyncContextManager

from grpc.aio import Channel, secure_channel, insecure_channel
import grpc
import certifi


@asynccontextmanager
async def create_channel(
    with_cert=True,
    *,
    host: str,
    port: int,
    logger: Logger | None = None,
) -> AsyncIterator[Channel]:
    addr = f"{host}:{port}"

    if with_cert:
        with open(certifi.where(), "rb") as f:
            cert = f.read()
        creds = grpc.ssl_channel_credentials(cert)
        channel = secure_channel(addr, creds)
    else:
        channel = insecure_channel(addr)
        if logger is not None:
            logger.warning("[GRPC] Using insecure credentials.")

    try:
        yield channel
    finally:
        await channel.close()


class CreateChannelContext(Protocol):
    def __call__(self, addr: str) -> AsyncContextManager[Channel]: ...


def generate_create_channel_context(
    logger: Logger | None = None,
    with_cert=True,
) -> CreateChannelContext:
    @asynccontextmanager
    async def create_channel_context(addr: str) -> AsyncIterator[Channel]:
        host, port = addr.split(":")

        async with create_channel(
            with_cert, host=host, port=int(port), logger=logger
        ) as channel:
            yield channel

    return create_channel_context

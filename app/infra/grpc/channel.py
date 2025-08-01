from contextlib import asynccontextmanager
from logging import Logger
from pathlib import Path
from typing import AsyncIterator, Protocol, AsyncContextManager, Sequence

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
    root_certificates: str | Sequence[str] | None = None,
) -> AsyncIterator[Channel]:
    addr = f"{host}:{port}"
    if host.endswith("."):
        normalized_host = host.rstrip(".")
    else:
        normalized_host = host

    if root_certificates is None:
        root_certificates = [certifi.where()]
    elif isinstance(root_certificates, str):
        root_certificates = [root_certificates]

    if with_cert:
        cert = b"".join(Path(path).read_bytes() for path in root_certificates)
        creds = grpc.ssl_channel_credentials(cert)
        options: list[tuple[str, str]] = []

        if host.endswith("."):
            options.append(("grpc.ssl_target_name_override", normalized_host))
            options.append(("grpc.default_authority", normalized_host))

        channel = secure_channel(addr, creds, options=options)
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
    *,
    root_certificates: str | Sequence[str] | None = None,
) -> CreateChannelContext:
    @asynccontextmanager
    async def create_channel_context(addr: str) -> AsyncIterator[Channel]:
        host, port = addr.split(":")

        async with create_channel(
            with_cert,
            host=host,
            port=int(port),
            logger=logger,
            root_certificates=root_certificates,
        ) as channel:
            yield channel

    return create_channel_context

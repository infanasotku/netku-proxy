from uuid import UUID
from typing import AsyncContextManager, AsyncIterator

from grpc.aio import Channel
from sentry_sdk import start_span

from app.infra.grpc.gen.xray_pb2_grpc import XrayStub
from app.infra.grpc.gen.xray_pb2 import XrayInfo

from app.infra.grpc.channel import CreateChannelContext
from app.infra.utils.retry import retry


class UUIDMismatchError(Exception):
    """
    Raised when the UUID received after restarting the engine does not match the expected UUID.

    Attributes:
        expected (UUID): The UUID that was originally sent with the restart request.
        received (UUID): The UUID that was received after the engine restarted.
    """

    def __init__(self, expected: UUID, received: UUID):
        super().__init__(f"Expected UUID {expected}, but received {received}.")
        self.expected = expected
        self.received = received


class GRPCEngineManager:
    def __init__(self, create_context: CreateChannelContext) -> None:
        self._create_context = create_context
        self._contexts: dict[str, AsyncContextManager[Channel]] = {}
        self._pull: dict[str, Channel] = {}

    async def _get_channel(self, addr: str) -> Channel:
        channel = self._pull.get(addr)
        if channel is None:
            context = self._create_context(addr)
            channel = await context.__aenter__()
            self._contexts[addr] = context
            self._pull[addr] = channel

        return channel

    async def close(self):
        for context in self._contexts.values():
            await context.__aexit__(None, None, None)

        self._pull.clear()
        self._contexts.clear()

    async def restart(self, uuid: UUID, *, addr: str):
        """
        Request a restart of the proxy engine and wait until it completes.

        This method sends a restart request to the engine, which will be restarted with the provided UUID as an access key.
        It blocks until the engine finishes restarting and responds with its new identity. If the returned UUID does not match the one originally
        sent, a UUIDMismatchError is raised.

        Args:
            uuid (UUID): The access key the engine will be restarted with. Users will connect to the engine using this key.
            addr (str): The address of the engine to restart, in 'host:port' format.

        Raises:
            UUIDMismatchError: If the UUID returned after restart does not match the expected one.
        """
        with start_span(op="grpc.client", name="Take gRPC channel"):
            channel = await self._get_channel(addr)

        @retry()
        async def _process() -> XrayInfo:
            stub = XrayStub(channel)
            return await stub.RestartXray(XrayInfo(uuid=str(uuid)))

        with start_span(op="grpc.client", name="Restart engine via gRPC") as span:
            span.set_tag("engine_addr", addr)

            resp = await _process()

        recieved_uuid = UUID(resp.uuid)
        if recieved_uuid != uuid:
            raise UUIDMismatchError(uuid, recieved_uuid)


async def create_grpc_manager(
    create_context: CreateChannelContext,
) -> AsyncIterator[GRPCEngineManager]:
    manager = GRPCEngineManager(create_context)

    try:
        yield manager
    finally:
        await manager.close()

from uuid import UUID
from typing import AsyncContextManager, AsyncIterator

from grpc.aio import Channel

from app.infra.grpc.gen.xray_pb2_grpc import XrayStub
from app.infra.grpc.gen.xray_pb2 import XrayInfo

from app.contracts.clients.engine import EngineManager, UUIDMismatchError
from app.infra.grpc.channel import CreateChannelContext


class GRPCEngineManager(EngineManager):
    def __init__(self, create_context: CreateChannelContext) -> None:
        self._create_context = create_context
        self._contexts: dict[str, AsyncContextManager[Channel]] = {}
        self._pull: dict[str, Channel]

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
        channel = await self._get_channel(addr)

        stub = XrayStub(channel)
        resp: XrayInfo = await stub.RestartXray(XrayInfo(uuid=str(uuid)))
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

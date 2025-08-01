from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.domains.event import DomainEvent
from app.domains.domain import Domain


@dataclass(frozen=True)
class Version:
    ts: int  # milliseconds
    seq: int  # counter

    @classmethod
    def from_stream_id(cls, sid: str) -> "Version":
        """Construct new `Version` object from stream_id: `timestamp`-`seq`."""
        ts, seq = map(int, sid.split("-", 1))
        return cls(ts, seq)

    def to_stream_id(self) -> str:
        return f"{self.ts}-{self.seq}"


class EngineStatus(StrEnum):
    ACTIVE = "active"
    READY = "ready"
    DEAD = "dead"


@dataclass(frozen=True, slots=True)
class EngineDead(DomainEvent):
    pass


@dataclass(frozen=True, slots=True)
class EngineUpdated(DomainEvent):
    new_uuid: UUID | None
    new_status: EngineStatus


@dataclass
class Engine(Domain):
    id: UUID
    uuid: UUID | None  # uuid from engine
    status: EngineStatus
    created: datetime
    addr: str
    version: Version

    def _is_newer(self, version: Version):
        if version.ts < self.version.ts or (
            version.ts == self.version.ts and version.seq <= self.version.seq
        ):
            return False
        return True

    def update(self, running: bool, uuid: UUID | None = None, *, version: Version):
        if not self._is_newer(version):
            return

        status = EngineStatus.ACTIVE if running else EngineStatus.READY
        self.status = status
        self.uuid = uuid
        self.version = version

        event = EngineUpdated(
            aggregate_id=self.id,
            version=version.to_stream_id(),
            new_uuid=uuid,
            new_status=status,
        )
        self._events.append(event)

    def remove(self, version: Version):
        if not self._is_newer(version):
            return

        self.status = EngineStatus.DEAD
        self.version = version

        event = EngineDead(self.id, version.to_stream_id())
        self._events.append(event)

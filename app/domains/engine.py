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


@dataclass(frozen=True, slots=True)
class EngineRestored(DomainEvent):
    uuid: UUID | None
    status: EngineStatus


@dataclass(unsafe_hash=True)
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

        old_hash = hash(self)

        status = EngineStatus.ACTIVE if running else EngineStatus.READY
        self.status = status
        self.uuid = uuid
        self.version = version

        new_hash = hash(self)

        if old_hash == new_hash:
            return

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

    def restore(self, running: bool, uuid: UUID | None = None, *, version: Version):
        if not self._is_newer(version):
            return

        self.status = EngineStatus.ACTIVE if running else EngineStatus.READY
        self.uuid = uuid
        self.version = version

        event = EngineRestored(self.id, version.to_stream_id(), uuid, self.status)
        self._events.append(event)

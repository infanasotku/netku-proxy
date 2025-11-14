from dataclasses import dataclass, field, fields
from datetime import datetime, timezone
from typing import Any, ClassVar, Self, Type, TypedDict, cast
from uuid import NAMESPACE_URL, UUID, uuid5


class DomainDict(TypedDict):
    # Meta fields
    aggregate_id: str
    version: str
    id: str
    occurred_at: str
    event_type: str

    # Payload fields
    payload: dict[str, Any]


@dataclass(frozen=True, slots=True)
class DomainEvent:
    aggregate_id: UUID
    version: str

    # Internal fields
    id: UUID = field(init=False)  # Deterministic field
    occurred_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc), init=False
    )

    _registry: ClassVar[dict[str, Type["DomainEvent"]]] = {}

    def __post_init__(self):
        object.__setattr__(  # workaround with frozen=True
            self,
            "id",
            uuid5(
                NAMESPACE_URL,
                f"{self.aggregate_id}:{self.version}:{self.__class__.__name__}",
            ),
        )

    def __init_subclass__(cls):
        DomainEvent._registry[cls.__name__] = cls

    def to_dict(self) -> DomainDict:
        """Envelope ready for JSON → broker."""
        meta: DomainDict = {
            "event_type": self.__class__.__name__,
            "id": str(self.id),
            "aggregate_id": str(self.aggregate_id),
            "version": self.version,
            "occurred_at": self.occurred_at.isoformat(timespec="milliseconds"),
            "payload": {},
        }

        meta_fields = {
            "aggregate_id",
            "version",
            "occurred_at",
            "id",
            "event_type",
        }
        payload = {
            f.name: getattr(self, f.name)
            for f in fields(self)
            if f.name not in meta_fields
        }
        meta["payload"] = payload
        return meta

    @classmethod
    def from_dict(cls: type[Self], data: dict[str, Any]) -> Self:
        name = data["event_type"]
        ev_cls = cast(type[Self], DomainEvent._registry[name])
        payload = data.get("payload", {})

        kwargs: dict[str, Any] = {
            "aggregate_id": UUID(data["aggregate_id"]),
            "version": data["version"],
            **payload,
        }

        obj: Self = ev_cls(**kwargs)
        object.__setattr__(obj, "id", UUID(data["id"]))
        object.__setattr__(
            obj, "occurred_at", datetime.fromisoformat(data["occurred_at"])
        )
        return obj

    @property
    def name(self) -> str:
        return self.__class__.__name__

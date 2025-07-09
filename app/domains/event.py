from dataclasses import dataclass, fields, field
from datetime import datetime
from typing import Any, Type, ClassVar, cast, Self
from uuid import UUID, uuid5, NAMESPACE_URL


@dataclass(frozen=True, slots=True)
class DomainEvent:
    aggregate_id: UUID
    version: str

    # Internal fields
    id: UUID = field(init=False)
    occurred_at: datetime = field(default_factory=datetime.now, init=False)

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

    def __init_subclass__(cls, **kw):
        super().__init_subclass__(**kw)
        DomainEvent._registry[cls.__name__] = cls

    def to_dict(self) -> dict[str, Any]:
        """Envelope ready for JSON → broker."""
        meta: dict[str, Any] = {
            "event_type": self.__class__.__name__,
            "id": str(self.id),
            "aggregate_id": str(self.aggregate_id),
            "version": self.version,
            "occurred_at": self.occurred_at.isoformat(timespec="milliseconds"),
        }

        meta_fields = {"aggregate_id", "version", "occurred_at", "id"}
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

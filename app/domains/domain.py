from dataclasses import dataclass, field

from app.domains.event import DomainEvent


@dataclass
class BaseDomain:
    _events: list[DomainEvent] = field(default_factory=list, init=False, repr=False)

    def pull_events(self) -> list[DomainEvent]:
        ev, self._events = self._events, []
        return ev

from app.domains.event import DomainEvent


def from_event(event: DomainEvent) -> str:
    dump = event.to_dict()

    return f"Event notification: {event.name}\n\nData: {dump['payload']}"

from aiogram.utils.markdown import hbold, hcode
from app.domains.event import DomainEvent


def from_event(event: DomainEvent) -> str:
    dump = event.to_dict()

    return (
        f"Event notification: {hbold(event.name)}\n\nData:\n {hcode(dump['payload'])}"
    )

import json

from aiogram.utils.markdown import hbold, hcode
from app.domains.event import DomainEvent


def from_event(event: DomainEvent) -> str:
    dump = event.to_dict()
    prettyfied = json.dumps(dump, indent=2)

    return f"Event notification: {hbold(event.name)}\n\nData:\n {hcode(prettyfied)}"

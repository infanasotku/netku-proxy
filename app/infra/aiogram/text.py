import json

from aiogram.utils.markdown import hbold, hcode
from app.domains.event import DomainEvent


def from_event(event: DomainEvent) -> str:
    dump = event.to_dict()
    payload = dump["payload"]
    prettyfied = json.dumps(payload, indent=2)

    return f"Event notification: {hbold(event.name)}\nEngine: {hbold(event.aggregate_id)}\nData:\n{hcode(prettyfied)}"

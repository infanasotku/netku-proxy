from datetime import timedelta

from faststream.rabbit import RabbitQueue

from app.infra.rabbit.exchanges import dlx_exchange

dead_letter_queue = RabbitQueue(
    name="dead_letters", durable=True, routing_key="dead_letters"
)

_message_seconds_ttl = int(timedelta(minutes=5).total_seconds())
QUEUE_ARGS = {
    "durable": True,
    "arguments": {
        "x-dead-letter-routing-key": dead_letter_queue.routing_key,
        "x-dead-letter-exchange": dlx_exchange.name,
        "x-message-ttl": _message_seconds_ttl * 1000,
        "x-max-priority": 9,
    },
}

proxy_engine_queue = RabbitQueue(name="proxy_engine_queue", **QUEUE_ARGS)
scope_info_queue = RabbitQueue(name="client_scope_queue")  # Readonly queue

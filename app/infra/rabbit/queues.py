from faststream.rabbit import RabbitQueue

from app.infra.rabbit.exchanges import dlx_exchange

dead_letter_queue = RabbitQueue(
    name="proxy_engine_dead_letters",
    durable=True,
    routing_key="proxy_engine_dead_letters",
    arguments={
        "x-dead-letter-routing-key": "proxy_engine_queue",
        "x-dead-letter-exchange": "",
        "x-message-ttl": 1000,
    },
)

QUEUE_ARGS = {
    "durable": True,
    "arguments": {
        "x-dead-letter-routing-key": dead_letter_queue.routing_key,
        "x-dead-letter-exchange": dlx_exchange.name,
    },
}

proxy_engine_queue = RabbitQueue(name="proxy_engine_queue", **QUEUE_ARGS)
scope_info_queue = RabbitQueue(name="client_scope_queue")  # Readonly queue

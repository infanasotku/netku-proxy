from app.infra.rabbit.exchanges import dlx_exchange
from app.infra.rabbit.queues import dead_letter_queue

__all__ = ["dlx_exchange", "dead_letter_queue"]

from faststream.rabbit import RabbitRouter

from app.infra.rabbit.queues import scope_info_queue


router = RabbitRouter()


@router.subscriber(scope_info_queue)
async def handle_client_scope_changed_event(msg):
    print(msg)

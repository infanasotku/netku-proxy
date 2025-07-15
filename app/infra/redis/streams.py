from uuid import uuid4
import socket

from faststream.redis import StreamSub

GROUP = "xray_engines"
CONSUMER = f"{socket.gethostname()}-{uuid4()}"

engine_stream = StreamSub(
    "xray_engines_keyevent_stream", group=GROUP, consumer=CONSUMER
)
dlq_stream = StreamSub("dlq_stream", group=GROUP, consumer=CONSUMER)

IDLE_MS = 60_000
BATCH = 100
PAUSE = 5
MAX_RETRY = 2

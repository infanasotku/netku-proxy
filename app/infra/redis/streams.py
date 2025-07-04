from uuid import uuid4

from faststream.redis import StreamSub

engine_stream = StreamSub(
    "xray_engines_keyevent_stream", group="xray_engines", consumer=uuid4().hex
)

import asyncio
import random


def retry(
    max_attempts: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    jitter: float = 0.1,
):  # -> Callable[..., Callable[..., CoroutineType[Any, Any, Any |...:
    def decorator(func):
        async def wrapper(*args, **kwargs):
            current_delay = delay
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                        current_delay += random.uniform(0, jitter)
                    else:
                        raise e

        return wrapper

    return decorator

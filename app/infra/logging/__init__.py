from logging import Logger
from typing import Callable
import traceback
from app.infra.logging.logger import logger, config

__all__ = ["logger", "config"]


async def with_logging(func: Callable, logger: Logger = logger, *args, **kwargs):
    try:
        await func(*args, **kwargs)
    except Exception as e:
        logger.error("\n".join([str(e), traceback.format_exc()]))

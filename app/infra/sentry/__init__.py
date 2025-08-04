from typing import Any, Callable

import sentry_sdk
from sentry_sdk.types import Event, Hint

from app.infra.config.settings import settings


def init_sentry(
    *,
    traces_sampler: Callable[[Any], float] | None = None,
    before_send_transaction: Callable[[Event, Hint], Any] | None = None,
):
    traces_sample_rate = None
    if traces_sampler is None:
        traces_sample_rate = 1.0

    sentry_sdk.init(
        dsn=settings.sentry.dsn,
        traces_sampler=traces_sampler,
        traces_sample_rate=traces_sample_rate,
        send_default_pii=True,
        before_send_transaction=before_send_transaction,
    )

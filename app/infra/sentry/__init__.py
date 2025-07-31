import sentry_sdk

from app.infra.config.settings import settings

sentry_sdk.init(dsn=settings.sentry.dsn, traces_sample_rate=1.0, debug=True)

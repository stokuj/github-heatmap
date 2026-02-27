import sentry_sdk

from backend.settings import Settings


def init_sentry(app_settings: Settings) -> None:
    """Initialize Sentry SDK when DSN is configured."""

    if not app_settings.sentry_dsn:
        return

    sentry_sdk.init(
        dsn=app_settings.sentry_dsn,
        environment=app_settings.environment,
        release=app_settings.release,
        traces_sample_rate=app_settings.sentry_traces_sample_rate,
        send_default_pii=False,
    )

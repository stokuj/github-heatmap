from backend.core.observability import init_sentry
from backend.settings import Settings


def test_init_sentry_skips_when_dsn_missing(monkeypatch) -> None:
    """Sentry initialization is skipped when DSN is absent."""

    calls: list[dict[str, object]] = []

    def fake_init(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("backend.core.observability.sentry_sdk.init", fake_init)

    settings = Settings(sentry_dsn=None)
    init_sentry(settings)

    assert calls == []


def test_init_sentry_initializes_sdk_with_settings(monkeypatch) -> None:
    """Sentry SDK is initialized with configured runtime settings."""

    calls: list[dict[str, object]] = []

    def fake_init(**kwargs):
        calls.append(kwargs)

    monkeypatch.setattr("backend.core.observability.sentry_sdk.init", fake_init)

    settings = Settings(
        sentry_dsn="https://examplePublicKey@o0.ingest.sentry.io/0",
        environment="production",
        release="abc123",
        sentry_traces_sample_rate=0.2,
    )
    init_sentry(settings)

    assert len(calls) == 1
    assert calls[0] == {
        "dsn": "https://examplePublicKey@o0.ingest.sentry.io/0",
        "environment": "production",
        "release": "abc123",
        "traces_sample_rate": 0.2,
        "send_default_pii": False,
    }

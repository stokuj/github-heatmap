from fastapi.testclient import TestClient

from backend.main import create_app


def test_heatmap_endpoint_rate_limited_after_threshold(monkeypatch) -> None:
    """Rate limiter blocks repeated requests to /heatmap/me."""

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    app = create_app()
    client = TestClient(app)

    headers = {"X-Forwarded-For": "203.0.113.10"}

    first = client.get("/heatmap/me", headers=headers)
    second = client.get("/heatmap/me", headers=headers)

    assert first.status_code == 401
    assert second.status_code == 429
    assert second.headers["Retry-After"]


def test_non_heatmap_routes_not_rate_limited(monkeypatch) -> None:
    """Rate limiter does not affect routes other than /heatmap/me."""

    monkeypatch.setenv("RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("RATE_LIMIT_WINDOW_SECONDS", "60")
    app = create_app()
    client = TestClient(app)

    first = client.get("/")
    second = client.get("/")

    assert first.status_code == 200
    assert second.status_code == 200

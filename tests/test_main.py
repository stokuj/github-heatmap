import httpx
from fastapi.testclient import TestClient

from backend.main import app


client = TestClient(app)


def test_read_root_returns_hello_world() -> None:
    """Root endpoint returns the expected hello payload."""

    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_live_returns_ok() -> None:
    """Liveness endpoint returns healthy status."""

    response = client.get("/health/live")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_sentry_debug_returns_500() -> None:
    """Sentry debug endpoint raises an internal server error."""

    debug_client = TestClient(app, raise_server_exceptions=False)

    response = debug_client.get("/sentry-debug")

    assert response.status_code == 500


def test_sentry_debug_returns_404_outside_development(monkeypatch) -> None:
    """Sentry debug endpoint is hidden when environment is not development."""

    debug_client = TestClient(app, raise_server_exceptions=False)
    monkeypatch.setattr("backend.api.routes.heatmap.settings.environment", "production")

    response = debug_client.get("/sentry-debug")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}


def test_get_heatmap_me_requires_bearer_token() -> None:
    """Heatmap endpoint rejects requests without bearer token."""

    response = client.get("/heatmap/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization Bearer token is required"}


def test_get_heatmap_me_rejects_non_bearer_authorization() -> None:
    """Heatmap endpoint rejects non-bearer authorization schemes."""

    response = client.get("/heatmap/me", headers={"Authorization": "token abc"})

    assert response.status_code == 401
    assert response.json() == {"detail": "Authorization Bearer token is required"}


def test_get_heatmap_me_returns_weeks_for_authenticated_user(monkeypatch) -> None:
    """Heatmap endpoint returns grouped weekly payload for valid auth."""

    def fake_fetch_authenticated_user(token: str) -> dict[str, str | int]:
        assert token == "oauth-token"
        return {"id": 1, "login": "OctoCat"}

    def fake_fetch_contribution_days(
        username: str,
        token: str,
        graphql_url: str,
    ):
        assert username == "octocat"
        assert token == "oauth-token"
        assert graphql_url == "https://api.github.com/graphql"
        return [
            {"date": "2026-02-15", "count": 0},
            {"date": "2026-02-16", "count": 2},
            {"date": "2026-02-17", "count": 10},
        ]

    monkeypatch.setattr(
        "backend.services.heatmap_service.fetch_authenticated_user",
        fake_fetch_authenticated_user,
    )
    monkeypatch.setattr(
        "backend.services.heatmap_service.fetch_contribution_days",
        fake_fetch_contribution_days,
    )

    response = client.get(
        "/heatmap/me",
        headers={"Authorization": "Bearer oauth-token"},
    )

    assert response.status_code == 200
    assert response.json() == {
        "username": "octocat",
        "total": 12,
        "weeks": [
            {
                "week_start": "2026-02-15",
                "days": [
                    {"date": "2026-02-15", "weekday": 0, "count": 0, "level": 0},
                    {"date": "2026-02-16", "weekday": 1, "count": 2, "level": 1},
                    {"date": "2026-02-17", "weekday": 2, "count": 10, "level": 4},
                ],
            }
        ],
    }


def test_get_heatmap_me_maps_github_auth_error_to_401(monkeypatch) -> None:
    """GitHub auth failure is translated into API 401 response."""

    def fake_fetch_authenticated_user(token: str) -> dict[str, str | int]:
        request = httpx.Request("GET", "https://api.github.com/user")
        response = httpx.Response(status_code=401, request=request)
        raise httpx.HTTPStatusError("Unauthorized", request=request, response=response)

    monkeypatch.setattr(
        "backend.services.heatmap_service.fetch_authenticated_user",
        fake_fetch_authenticated_user,
    )

    response = client.get(
        "/heatmap/me",
        headers={"Authorization": "Bearer invalid-token"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "GitHub token is invalid"}


def test_openapi_exposes_bearer_auth_for_heatmap_me() -> None:
    """OpenAPI schema exposes bearer security for heatmap endpoint."""

    response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    security_schemes = payload["components"]["securitySchemes"]
    assert security_schemes["HTTPBearer"] == {
        "type": "http",
        "scheme": "bearer",
    }
    operation = payload["paths"]["/heatmap/me"]["get"]
    assert operation["security"] == [{"HTTPBearer": []}]

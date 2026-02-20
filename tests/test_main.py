import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from backend.db import Base
from backend.db import get_db
from backend.main import app
from backend.settings import Settings


client = TestClient(app)


@pytest.fixture
def db_client() -> TestClient:
    test_engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    testing_session_local = sessionmaker(
        bind=test_engine,
        autoflush=False,
        autocommit=False,
    )

    Base.metadata.create_all(bind=test_engine)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()


def test_read_root_returns_hello_world() -> None:
    response = client.get("/")

    assert response.status_code == 200
    assert response.json() == {"message": "Hello World"}


def test_health_db_returns_ok_for_valid_database_url(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "sqlite+pysqlite:///:memory:")

    response = client.get("/health/db")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_db_returns_500_when_database_url_empty(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "")

    response = client.get("/health/db")

    assert response.status_code == 500
    assert response.json() == {"detail": "DATABASE_URL is not set"}


def test_settings_reads_database_url_from_environment(monkeypatch) -> None:
    monkeypatch.setenv("DATABASE_URL", "postgresql+psycopg://u:p@localhost:5432/db")

    settings = Settings()

    assert settings.database_url == "postgresql+psycopg://u:p@localhost:5432/db"


def test_create_profile_returns_201(db_client: TestClient) -> None:
    response = db_client.post("/profiles", json={"username": "octocat"})

    assert response.status_code == 201
    assert response.json()["username"] == "octocat"


def test_create_heatmap_day_and_read_heatmap(db_client: TestClient) -> None:
    db_client.post("/profiles", json={"username": "octocat"})

    create_day_response = db_client.post(
        "/profiles/octocat/days",
        json={"day": "2026-02-20", "count": 7},
    )
    heatmap_response = db_client.get("/heatmap/octocat")

    assert create_day_response.status_code == 200
    assert create_day_response.json() == {"day": "2026-02-20", "count": 7}
    assert heatmap_response.status_code == 200
    assert heatmap_response.json() == [{"day": "2026-02-20", "count": 7}]


def test_sync_profile_fetches_events_and_rebuilds_heatmap(
    monkeypatch: pytest.MonkeyPatch, db_client: TestClient
) -> None:
    db_client.post("/profiles", json={"username": "octocat"})

    def fake_fetch_user_events(username: str, token: str | None, api_base_url: str):
        assert username == "octocat"
        return [
            {
                "id": "1001",
                "type": "PushEvent",
                "created_at": "2026-02-20T10:00:00Z",
                "repo": {"name": "octocat/hello"},
            },
            {
                "id": "1002",
                "type": "IssuesEvent",
                "created_at": "2026-02-20T12:00:00Z",
                "repo": {"name": "octocat/hello"},
            },
            {
                "id": "1003",
                "type": "PushEvent",
                "created_at": "2026-02-19T08:00:00Z",
                "repo": {"name": "octocat/demo"},
            },
        ]

    monkeypatch.setattr("backend.main.fetch_user_events", fake_fetch_user_events)

    sync_response = db_client.post("/profiles/octocat/sync")
    heatmap_response = db_client.get("/heatmap/octocat")

    assert sync_response.status_code == 200
    assert sync_response.json() == {
        "status": "ok",
        "fetched": 3,
        "saved": 3,
        "days_updated": 2,
    }
    assert heatmap_response.status_code == 200
    assert heatmap_response.json() == [
        {"day": "2026-02-19", "count": 1},
        {"day": "2026-02-20", "count": 2},
    ]


def test_sync_profile_returns_404_for_missing_profile(db_client: TestClient) -> None:
    response = db_client.post("/profiles/unknown-user/sync")

    assert response.status_code == 404
    assert response.json() == {"detail": "profile not found"}


def test_get_calendar_heatmap_returns_zero_filled_range(db_client: TestClient) -> None:
    db_client.post("/profiles", json={"username": "octocat"})
    db_client.post("/profiles/octocat/days", json={"day": "2026-02-19", "count": 2})
    db_client.post("/profiles/octocat/days", json={"day": "2026-02-21", "count": 1})

    response = db_client.get("/heatmap/octocat/calendar?from=2026-02-18&to=2026-02-21")

    assert response.status_code == 200
    assert response.json() == {
        "username": "octocat",
        "from": "2026-02-18",
        "to": "2026-02-21",
        "total": 3,
        "days": [
            {"date": "2026-02-18", "count": 0},
            {"date": "2026-02-19", "count": 2},
            {"date": "2026-02-20", "count": 0},
            {"date": "2026-02-21", "count": 1},
        ],
    }


def test_get_calendar_heatmap_rejects_invalid_date_range(db_client: TestClient) -> None:
    db_client.post("/profiles", json={"username": "octocat"})

    response = db_client.get("/heatmap/octocat/calendar?from=2026-02-22&to=2026-02-21")

    assert response.status_code == 400
    assert response.json() == {"detail": "from must be before or equal to to"}

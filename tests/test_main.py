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

    def fake_fetch_contribution_days(
        username: str,
        token: str,
        graphql_url: str,
    ):
        assert username == "octocat"
        assert token == "test-token"
        assert graphql_url == "https://api.github.com/graphql"
        return [
            {"date": "2026-02-20", "count": 2},
            {"date": "2026-02-19", "count": 28},
            {"date": "2025-04-13", "count": 1},
        ]

    monkeypatch.setattr(
        "backend.main.fetch_contribution_days", fake_fetch_contribution_days
    )
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")

    sync_response = db_client.post("/profiles/octocat/sync")
    heatmap_response = db_client.get("/heatmap/octocat")

    assert sync_response.status_code == 200
    assert sync_response.json() == {
        "status": "ok",
        "fetched": 3,
        "saved": 3,
        "days_updated": 3,
    }
    assert heatmap_response.status_code == 200
    assert heatmap_response.json() == [
        {"day": "2025-04-13", "count": 1},
        {"day": "2026-02-19", "count": 28},
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


def test_get_calendar_grid_returns_github_style_weeks(db_client: TestClient) -> None:
    db_client.post("/profiles", json={"username": "octocat"})
    db_client.post("/profiles/octocat/days", json={"day": "2026-02-19", "count": 2})
    db_client.post("/profiles/octocat/days", json={"day": "2026-02-20", "count": 7})

    response = db_client.get(
        "/heatmap/octocat/calendar-grid?from=2026-02-18&to=2026-02-21"
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["username"] == "octocat"
    assert payload["from"] == "2026-02-18"
    assert payload["to"] == "2026-02-21"
    assert payload["total"] == 9
    assert payload["weekday_labels"] == [
        "Sun",
        "Mon",
        "Tue",
        "Wed",
        "Thu",
        "Fri",
        "Sat",
    ]
    assert payload["month_labels"] == [
        {"week_start": "2026-02-15", "month": "2026-02", "label": "Feb"}
    ]
    assert payload["weeks"][0]["week_start"] == "2026-02-15"
    assert len(payload["weeks"]) == 1

    flattened_days = [day for week in payload["weeks"] for day in week["days"]]
    day_map = {day["date"]: day for day in flattened_days}

    assert day_map["2026-02-18"] == {
        "date": "2026-02-18",
        "weekday": 3,
        "count": 0,
        "level": 0,
    }
    assert day_map["2026-02-19"] == {
        "date": "2026-02-19",
        "weekday": 4,
        "count": 2,
        "level": 1,
    }
    assert day_map["2026-02-20"] == {
        "date": "2026-02-20",
        "weekday": 5,
        "count": 7,
        "level": 3,
    }


def test_get_calendar_grid_requires_complete_date_range(db_client: TestClient) -> None:
    db_client.post("/profiles", json={"username": "octocat"})

    response = db_client.get("/heatmap/octocat/calendar-grid?from=2026-02-01")

    assert response.status_code == 400
    assert response.json() == {"detail": "from and to must be provided together"}


def test_get_heatmap_meta_returns_weekday_and_level_labels() -> None:
    response = client.get("/meta/heatmap")

    assert response.status_code == 200
    assert response.json() == {
        "weekday_labels": ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"],
        "levels": [
            {"level": 0, "label": "0", "min": 0, "max": 0},
            {"level": 1, "label": "1-2", "min": 1, "max": 2},
            {"level": 2, "label": "3-5", "min": 3, "max": 5},
            {"level": 3, "label": "6-9", "min": 6, "max": 9},
            {"level": 4, "label": "10+", "min": 10, "max": None},
        ],
    }


def test_demo_endpoint_returns_html() -> None:
    response = client.get("/demo/octocat")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert "GitHub Heatmap Demo" in response.text
    assert "/heatmap/${username}/calendar-grid" in response.text

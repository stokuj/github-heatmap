from fastapi.testclient import TestClient

from backend.main import app
from backend.settings import Settings


client = TestClient(app)


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

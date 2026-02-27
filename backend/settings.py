from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables.

    Values are read from process environment and optionally from `.env`.
    """

    github_graphql_url: str = "https://api.github.com/graphql"
    sentry_dsn: str | None = None
    environment: str = "development"
    release: str | None = None
    sentry_traces_sample_rate: float = 0.1
    rate_limit_per_minute: int = 30
    rate_limit_window_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

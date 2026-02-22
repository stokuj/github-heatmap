from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    github_graphql_url: str = "https://api.github.com/graphql"
    sentry_dsn: str | None = None
    environment: str = "development"
    release: str | None = None
    sentry_traces_sample_rate: float = 0.1

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

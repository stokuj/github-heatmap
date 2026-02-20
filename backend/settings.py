from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    github_token: str | None = None
    github_graphql_url: str = "https://api.github.com/graphql"
    sync_cooldown_seconds: int = 60
    sync_max_per_hour: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

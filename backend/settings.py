from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    github_token: str | None = None
    github_graphql_url: str = "https://api.github.com/graphql"
    github_oauth_client_id: str | None = None
    github_oauth_client_secret: str | None = None
    app_base_url: str = "http://127.0.0.1:8000"
    sync_cooldown_seconds: int = 60
    sync_max_per_hour: int = 12

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

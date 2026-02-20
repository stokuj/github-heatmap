from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    database_url: str | None = None
    github_token: str | None = None
    github_api_base_url: str = "https://api.github.com"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

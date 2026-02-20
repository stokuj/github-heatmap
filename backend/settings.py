from pydantic_settings import BaseSettings
from pydantic_settings import SettingsConfigDict


class Settings(BaseSettings):
    github_graphql_url: str = "https://api.github.com/graphql"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

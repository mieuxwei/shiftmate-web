from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_env: str = "development"
    app_timezone: str = "Asia/Taipei"
    frontend_dist_dir: Path = Field(default=Path("frontend/dist"))


@lru_cache
def get_settings() -> Settings:
    return Settings()

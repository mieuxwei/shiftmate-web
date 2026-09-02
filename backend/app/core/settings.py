from functools import lru_cache
from pathlib import Path

from pydantic import Field, HttpUrl
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
    supabase_url: HttpUrl | None = None
    supabase_jwt_audience: str = "authenticated"
    database_url: str | None = None
    database_request_role: str = "authenticated"
    database_pool_size: int = Field(default=2, ge=1, le=5)
    database_max_overflow: int = Field(default=0, ge=0, le=5)


@lru_cache
def get_settings() -> Settings:
    return Settings()

from functools import lru_cache
from pathlib import Path
from typing import Literal

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
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: Literal[768] = 768
    gemini_timeout_seconds: float = Field(default=30, gt=0, le=120)
    rag_top_k: int = Field(default=5, ge=1, le=10)
    rag_score_threshold: float = Field(default=0.55, ge=-1, le=1)
    upload_max_bytes: int = Field(default=5 * 1024 * 1024, ge=1)
    upload_pdf_max_pages: int = Field(default=40, ge=1, le=40)
    upload_daily_cap_per_owner: int = Field(default=10, ge=1, le=100)
    gemini_daily_request_cap: int = Field(default=50, ge=1, le=1000)
    api_rate_limit_per_minute: int = Field(default=120, ge=1, le=1000)
    google_oauth_client_id: str | None = None
    google_oauth_client_secret: str | None = None
    google_oauth_redirect_uri: str | None = None
    google_oauth_state_secret: str | None = None
    calendar_token_encryption_key: str | None = None
    google_oauth_timeout_seconds: float = Field(default=15, gt=0, le=60)
    mcp_allowed_hosts: list[str] = Field(
        default_factory=lambda: ["127.0.0.1:*", "localhost:*", "test"]
    )
    mcp_allowed_origins: list[str] = Field(
        default_factory=lambda: [
            "http://127.0.0.1:*",
            "http://localhost:*",
            "http://test",
        ]
    )
    scheduler_oidc_audience: str | None = None
    scheduler_service_account_email: str | None = None
    scheduler_job_name: str = "daily-maintenance"
    database_maintenance_role: str = "shiftmate_maintenance"
    maintenance_draft_ttl_days: int = Field(default=7, ge=1, le=30)
    maintenance_retention_days: int = Field(default=30, ge=7, le=90)


@lru_cache
def get_settings() -> Settings:
    return Settings()

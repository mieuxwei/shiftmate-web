from collections.abc import Callable
from dataclasses import dataclass
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import Engine, text

from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.database import (
    authenticated_connection,
    build_quota_engine,
    get_database_engine,
)
from backend.app.core.settings import Settings, get_settings


class QuotaExceededError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class RequestQuotaGuard:
    engine: Engine
    user: AuthenticatedUser
    gemini_daily_limit: int
    upload_daily_limit: int

    def consume_upload(self) -> None:
        self._consume(
            "app_private.consume_owner_daily_quota",
            "upload",
            self.upload_daily_limit,
            "UPLOAD_DAILY_QUOTA_EXCEEDED",
        )

    def consume_gemini_request(self) -> None:
        self._consume(
            "app_private.consume_app_daily_quota",
            "gemini_request",
            self.gemini_daily_limit,
            "GEMINI_DAILY_CAP_EXCEEDED",
        )

    def _consume(
        self, function_name: str, quota_name: str, limit: int, error_code: str
    ) -> None:
        with authenticated_connection(self.engine, self.user) as connection:
            allowed = connection.execute(
                text(f"SELECT {function_name}(:quota_name, :quota_limit)"),
                {"quota_name": quota_name, "quota_limit": limit},
            ).scalar_one()
        if not allowed:
            raise QuotaExceededError(error_code)


def get_request_quota_guard(
    engine: Annotated[Engine, Depends(get_database_engine)],
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> RequestQuotaGuard:
    quota_engine = build_quota_engine(engine.url.render_as_string(hide_password=False))
    return RequestQuotaGuard(
        quota_engine,
        user,
        settings.gemini_daily_request_cap,
        settings.upload_daily_cap_per_owner,
    )


def consume_upload_quota(
    guard: Annotated[RequestQuotaGuard, Depends(get_request_quota_guard)],
) -> None:
    try:
        guard.consume_upload()
    except QuotaExceededError as error:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=error.code,
            headers={"Retry-After": "86400"},
        ) from error


def quota_callback(guard: RequestQuotaGuard) -> Callable[[], None]:
    return guard.consume_gemini_request

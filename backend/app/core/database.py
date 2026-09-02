from collections.abc import Iterator
from contextlib import contextmanager
from functools import lru_cache
from typing import Annotated

from fastapi import Depends, HTTPException, status
from sqlalchemy import Connection, Engine, create_engine, text
from sqlalchemy.pool import NullPool

from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.settings import Settings, get_settings


@lru_cache
def build_engine(url: str, pool_size: int, max_overflow: int) -> Engine:
    return create_engine(
        url,
        pool_pre_ping=True,
        pool_size=pool_size,
        max_overflow=max_overflow,
        connect_args={"prepare_threshold": None},
    )


@lru_cache
def build_quota_engine(url: str) -> Engine:
    return create_engine(
        url,
        poolclass=NullPool,
        pool_pre_ping=True,
        connect_args={"prepare_threshold": None},
    )


def get_database_engine(
    settings: Annotated[Settings, Depends(get_settings)],
) -> Engine:
    if settings.database_url is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Database is not configured",
        )
    if settings.database_request_role != "authenticated":
        raise RuntimeError("Ordinary requests must use the authenticated DB role")
    return build_engine(
        settings.database_url,
        settings.database_pool_size,
        settings.database_max_overflow,
    )


def user_connection(
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    engine: Annotated[Engine, Depends(get_database_engine)],
) -> Iterator[Connection]:
    with authenticated_connection(engine, user) as connection:
        yield connection


@contextmanager
def authenticated_connection(
    engine: Engine, user: AuthenticatedUser
) -> Iterator[Connection]:
    with engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE authenticated")
        connection.execute(
            text("SELECT set_config('request.jwt.claim.sub', :user_id, true)"),
            {"user_id": str(user.id)},
        )
        yield connection


@contextmanager
def maintenance_connection(engine: Engine, role: str) -> Iterator[Connection]:
    if role != "shiftmate_maintenance":
        raise RuntimeError("Maintenance database role is not allowlisted")
    with engine.begin() as connection:
        connection.exec_driver_sql("SET LOCAL ROLE shiftmate_maintenance")
        yield connection

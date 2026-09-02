from datetime import date
from functools import lru_cache
from typing import Annotated

from fastapi import APIRouter, Cookie, Depends, HTTPException, Query, Response, status
from fastapi.responses import RedirectResponse
from sqlalchemy import Connection, Engine

from backend.app.api.v1.shifts import get_shift_repository
from backend.app.core.auth import AuthenticatedUser, get_current_user
from backend.app.core.database import (
    authenticated_connection,
    get_database_engine,
    user_connection,
)
from backend.app.core.settings import Settings, get_settings
from backend.app.integrations.google_calendar import (
    GoogleCalendarClient,
    GoogleCalendarError,
)
from backend.app.repositories.calendar import (
    CalendarRepository,
    PostgresCalendarRepository,
)
from backend.app.repositories.shifts import ShiftRepository
from backend.app.schemas.calendar import (
    CalendarConnectResponse,
    CalendarStatusResponse,
    CalendarSyncResponse,
)
from backend.app.services.calendar import (
    CalendarService,
    CalendarServiceError,
    connection_expiry,
    effective_scopes,
)
from backend.app.services.calendar_exports import (
    CalendarExportError,
    CalendarExportService,
)
from backend.app.services.calendar_security import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    CalendarSecurityError,
    OAuthStateManager,
    SecretBox,
    build_authorization_url,
)

router = APIRouter(prefix="/calendar", tags=["calendar"])
OAUTH_COOKIE = "shiftmate_calendar_oauth"


@lru_cache
def get_calendar_repository() -> PostgresCalendarRepository:
    return PostgresCalendarRepository()


def _oauth_settings(settings: Settings) -> tuple[str, str, str, str, str]:
    values = (
        settings.google_oauth_client_id,
        settings.google_oauth_client_secret,
        settings.google_oauth_redirect_uri,
        settings.google_oauth_state_secret,
        settings.calendar_token_encryption_key,
    )
    if not all(values):
        raise HTTPException(status_code=503, detail="CALENDAR_NOT_CONFIGURED")
    return values  # type: ignore[return-value]


def _provider(settings: Settings) -> GoogleCalendarClient:
    client_id, client_secret, redirect_uri, _, _ = _oauth_settings(settings)
    return GoogleCalendarClient(
        client_id,
        client_secret,
        redirect_uri,
        settings.google_oauth_timeout_seconds,
    )


@router.get("/status", response_model=CalendarStatusResponse)
def calendar_status(
    connection: Annotated[Connection, Depends(user_connection)],
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> CalendarStatusResponse:
    configured = all(
        (
            settings.google_oauth_client_id,
            settings.google_oauth_client_secret,
            settings.google_oauth_redirect_uri,
            settings.google_oauth_state_secret,
            settings.calendar_token_encryption_key,
        )
    )
    record = repository.get_connection(connection)
    return CalendarStatusResponse(
        configured=configured,
        connection_status=record.status if record else "disconnected",
        scopes=list(record.scopes) if record else [],
    )


@router.get("/connect", response_model=CalendarConnectResponse)
def connect_calendar(
    response: Response,
    user: Annotated[AuthenticatedUser, Depends(get_current_user)],
    settings: Annotated[Settings, Depends(get_settings)],
    return_path: Annotated[str, Query(max_length=200)] = "/?calendar=connected",
) -> CalendarConnectResponse:
    client_id, _, redirect_uri, state_secret, _ = _oauth_settings(settings)
    try:
        cookie, state = OAuthStateManager(state_secret).issue(user.id, return_path)
    except CalendarSecurityError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    response.set_cookie(
        OAUTH_COOKIE,
        cookie,
        max_age=600,
        httponly=True,
        secure=settings.app_env not in {"development", "test"},
        samesite="lax",
        path="/api/v1/calendar/callback",
    )
    return CalendarConnectResponse(
        authorization_url=build_authorization_url(client_id, redirect_uri, state)
    )


@router.get("/callback")
async def calendar_callback(
    code: Annotated[str, Query(min_length=1, max_length=4096)],
    state: Annotated[str, Query(min_length=1, max_length=256)],
    settings: Annotated[Settings, Depends(get_settings)],
    engine: Annotated[Engine, Depends(get_database_engine)],
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    oauth_cookie: Annotated[str | None, Cookie(alias=OAUTH_COOKIE)] = None,
) -> RedirectResponse:
    _, _, _, state_secret, token_secret = _oauth_settings(settings)
    if not oauth_cookie:
        raise HTTPException(status_code=400, detail="OAUTH_STATE_MISSING")
    try:
        verified = OAuthStateManager(state_secret).verify(oauth_cookie, state)
    except CalendarSecurityError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    try:
        token = await _provider(settings).exchange_code(code, verified.code_verifier)
        scopes = effective_scopes(token)
        if GOOGLE_CALENDAR_EVENTS_SCOPE not in scopes:
            raise GoogleCalendarError("CALENDAR_SCOPE_MISSING")
        encrypted_token = (
            SecretBox(token_secret).encrypt(token.refresh_token)
            if token.refresh_token
            else None
        )
        callback_user = AuthenticatedUser(verified.owner_id, "authenticated")
        with authenticated_connection(engine, callback_user) as connection:
            existing = repository.get_connection(connection)
            if encrypted_token is None and existing is None:
                raise GoogleCalendarError("CALENDAR_REFRESH_TOKEN_MISSING")
            repository.save_connection(
                connection,
                encrypted_token,
                scopes,
                connection_expiry(token),
            )
        redirect = RedirectResponse(verified.return_path, status_code=303)
    except (GoogleCalendarError, CalendarSecurityError):
        redirect = RedirectResponse("/?calendar=error", status_code=303)
    redirect.delete_cookie(OAUTH_COOKIE, path="/api/v1/calendar/callback")
    return redirect


@router.post("/sync", response_model=CalendarSyncResponse)
async def sync_calendar(
    connection: Annotated[Connection, Depends(user_connection)],
    repository: Annotated[CalendarRepository, Depends(get_calendar_repository)],
    settings: Annotated[Settings, Depends(get_settings)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> CalendarSyncResponse:
    *_, token_secret = _oauth_settings(settings)
    try:
        result = await CalendarService(
            repository, _provider(settings), SecretBox(token_secret)
        ).sync(connection, date_from, date_to)
    except CalendarServiceError as error:
        code = (
            status.HTTP_409_CONFLICT
            if error.code in {"CALENDAR_NOT_CONNECTED", "CALENDAR_AUTH_REVOKED"}
            else status.HTTP_503_SERVICE_UNAVAILABLE
        )
        raise HTTPException(status_code=code, detail=error.code) from error
    return CalendarSyncResponse(
        synced=result.synced, deleted=result.deleted, failed=result.failed
    )


@router.get("/export.ics")
def export_calendar(
    connection: Annotated[Connection, Depends(user_connection)],
    shift_repository: Annotated[ShiftRepository, Depends(get_shift_repository)],
    date_from: Annotated[date | None, Query()] = None,
    date_to: Annotated[date | None, Query()] = None,
) -> Response:
    try:
        calendar_export = CalendarExportService(shift_repository).create_export(
            connection, date_from, date_to
        )
    except CalendarExportError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    return Response(
        calendar_export.content,
        media_type=calendar_export.media_type,
        headers={
            "Content-Disposition": (
                f'attachment; filename="{calendar_export.filename}"'
            )
        },
    )

import hashlib
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from typing import Any, Protocol

from sqlalchemy import Connection

from backend.app.integrations.google_calendar import (
    GoogleCalendarError,
    GoogleToken,
    GoogleTokenRevokedError,
)
from backend.app.repositories.calendar import CalendarRepository, CalendarSyncRecord
from backend.app.services.calendar_security import (
    GOOGLE_CALENDAR_EVENTS_SCOPE,
    CalendarSecurityError,
    SecretBox,
)


class CalendarProvider(Protocol):
    async def refresh(self, refresh_token: str) -> GoogleToken: ...

    async def upsert_event(
        self, access_token: str, event_id: str, event: dict[str, Any]
    ) -> None: ...

    async def delete_event(self, access_token: str, event_id: str) -> None: ...


class CalendarServiceError(RuntimeError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True, slots=True)
class CalendarStatus:
    configured: bool
    connection_status: str
    scopes: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class SyncSummary:
    synced: int
    deleted: int
    failed: int


class CalendarService:
    def __init__(
        self,
        repository: CalendarRepository,
        provider: CalendarProvider,
        token_box: SecretBox,
    ) -> None:
        self.repository = repository
        self.provider = provider
        self.token_box = token_box

    def status(self, connection: Connection, configured: bool = True) -> CalendarStatus:
        record = self.repository.get_connection(connection)
        return CalendarStatus(
            configured=configured,
            connection_status=record.status if record else "disconnected",
            scopes=record.scopes if record else (),
        )

    async def sync(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> SyncSummary:
        if date_from and date_to and date_to < date_from:
            raise CalendarServiceError("CALENDAR_DATE_RANGE_INVALID")
        calendar_connection = self.repository.get_connection(
            connection, for_update=True
        )
        if calendar_connection is None:
            raise CalendarServiceError("CALENDAR_NOT_CONNECTED")
        if calendar_connection.status != "active":
            raise CalendarServiceError("CALENDAR_AUTH_REVOKED")
        try:
            refresh_token = self.token_box.decrypt(
                calendar_connection.encrypted_refresh_token
            )
            token = await self.provider.refresh(refresh_token)
        except GoogleTokenRevokedError as error:
            self.repository.mark_connection_revoked(connection)
            raise CalendarServiceError("CALENDAR_AUTH_REVOKED") from error
        except CalendarSecurityError as error:
            raise CalendarServiceError("CALENDAR_TOKEN_INVALID") from error
        except GoogleCalendarError as error:
            raise CalendarServiceError(error.code) from error

        self.repository.ensure_sync_records(connection, date_from, date_to)
        records = self.repository.list_sync_records(connection, date_from, date_to)
        synced = deleted = failed = 0
        for record in records:
            try:
                if record.shift_id is None or record.status == "pending_delete":
                    if record.external_event_id:
                        await self.provider.delete_event(
                            token.access_token, record.external_event_id
                        )
                    self.repository.mark_sync_success(
                        connection,
                        record.id,
                        record.external_event_id,
                        deleted=True,
                    )
                    deleted += 1
                else:
                    event_id = record.external_event_id or stable_event_id(record)
                    await self.provider.upsert_event(
                        token.access_token, event_id, event_body(record)
                    )
                    self.repository.mark_sync_success(
                        connection, record.id, event_id, deleted=False
                    )
                    synced += 1
            except GoogleTokenRevokedError as error:
                self.repository.mark_connection_revoked(connection)
                raise CalendarServiceError("CALENDAR_AUTH_REVOKED") from error
            except GoogleCalendarError as error:
                self.repository.mark_sync_failure(connection, record.id, error.code)
                failed += 1
        return SyncSummary(synced=synced, deleted=deleted, failed=failed)


def connection_expiry(
    token: GoogleToken, now: datetime | None = None
) -> datetime | None:
    if token.expires_in is None:
        return None
    return (now or datetime.now(UTC)) + timedelta(seconds=token.expires_in)


def effective_scopes(token: GoogleToken) -> tuple[str, ...]:
    return token.scopes or (GOOGLE_CALENDAR_EVENTS_SCOPE,)


def stable_event_id(record: CalendarSyncRecord) -> str:
    if record.shift_id is None:
        raise CalendarServiceError("CALENDAR_SYNC_RECORD_INVALID")
    digest = hashlib.sha256(f"{record.owner_id}:{record.shift_id}".encode()).hexdigest()
    return f"shiftmate{digest}"


def event_body(record: CalendarSyncRecord) -> dict[str, Any]:
    if record.start_at is None or record.end_at is None or record.shift_type is None:
        raise CalendarServiceError("CALENDAR_SYNC_RECORD_INVALID")
    return {
        "summary": f"Shift · {record.shift_type}",
        "description": record.notes or "Synced from ShiftMate Web",
        "start": {"dateTime": record.start_at.isoformat()},
        "end": {"dateTime": record.end_at.isoformat()},
        "extendedProperties": {"private": {"shiftmateShiftId": str(record.shift_id)}},
    }

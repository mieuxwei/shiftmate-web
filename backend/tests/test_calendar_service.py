from dataclasses import replace
from datetime import UTC, date, datetime
from typing import Any, cast
from uuid import UUID

import pytest
from sqlalchemy import Connection

from backend.app.integrations.google_calendar import (
    GoogleCalendarError,
    GoogleToken,
    GoogleTokenRevokedError,
)
from backend.app.repositories.calendar import (
    CalendarConnectionRecord,
    CalendarSyncRecord,
)
from backend.app.services.calendar import CalendarService, CalendarServiceError
from backend.app.services.calendar_security import SecretBox

CONNECTION = cast(Connection, object())
OWNER_ID = UUID("00000000-0000-0000-0000-000000000703")
SHIFT_ID = UUID("00000000-0000-0000-0000-000000000704")
RECORD_ID = UUID("00000000-0000-0000-0000-000000000705")
SECRET = "synthetic-calendar-token-secret-32-characters"
pytestmark = pytest.mark.anyio


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


class FakeCalendarRepository:
    def __init__(self) -> None:
        self.box = SecretBox(SECRET)
        self.connection = CalendarConnectionRecord(
            owner_id=OWNER_ID,
            encrypted_refresh_token=self.box.encrypt("synthetic-refresh"),
            scopes=("https://www.googleapis.com/auth/calendar.events.owned",),
            expires_at=None,
            status="active",
        )
        self.records = [
            CalendarSyncRecord(
                id=RECORD_ID,
                owner_id=OWNER_ID,
                shift_id=SHIFT_ID,
                external_event_id=None,
                status="pending",
                retry_count=0,
                start_at=datetime(2026, 9, 2, 1, tzinfo=UTC),
                end_at=datetime(2026, 9, 2, 9, tzinfo=UTC),
                shift_type="day",
                notes="Synthetic shift truth",
            )
        ]

    def get_connection(
        self, connection: Connection, *, for_update: bool = False
    ) -> CalendarConnectionRecord | None:
        return self.connection

    def save_connection(
        self, *args: object, **kwargs: object
    ) -> CalendarConnectionRecord:
        return self.connection

    def mark_connection_revoked(self, connection: Connection) -> None:
        self.connection = replace(self.connection, status="revoked")

    def ensure_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> None:
        return None

    def list_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> list[CalendarSyncRecord]:
        return [record for record in self.records if record.status != "deleted"]

    def mark_sync_success(
        self,
        connection: Connection,
        record_id: UUID,
        event_id: str | None,
        deleted: bool,
    ) -> None:
        self.records = [
            replace(
                record,
                external_event_id=event_id,
                status="deleted" if deleted else "synced",
            )
            if record.id == record_id
            else record
            for record in self.records
        ]

    def mark_sync_failure(
        self, connection: Connection, record_id: UUID, error_code: str
    ) -> None:
        self.records = [
            replace(record, status="failed", retry_count=record.retry_count + 1)
            if record.id == record_id
            else record
            for record in self.records
        ]


class FakeProvider:
    def __init__(
        self,
        refresh_failure: Exception | None = None,
        event_failure: Exception | None = None,
    ) -> None:
        self.refresh_failure = refresh_failure
        self.event_failure = event_failure
        self.events: dict[str, dict[str, Any]] = {}
        self.deleted: list[str] = []

    async def refresh(self, refresh_token: str) -> GoogleToken:
        if self.refresh_failure:
            raise self.refresh_failure
        assert refresh_token == "synthetic-refresh"
        return GoogleToken("synthetic-access", None, 3600, ())

    async def upsert_event(
        self, access_token: str, event_id: str, event: dict[str, Any]
    ) -> None:
        if self.event_failure:
            raise self.event_failure
        self.events[event_id] = event

    async def delete_event(self, access_token: str, event_id: str) -> None:
        if self.event_failure:
            raise self.event_failure
        self.deleted.append(event_id)
        self.events.pop(event_id, None)


async def test_repeated_sync_uses_one_stable_external_event() -> None:
    repository = FakeCalendarRepository()
    provider = FakeProvider()
    service = CalendarService(repository, provider, repository.box)

    first = await service.sync(CONNECTION)
    first_id = repository.records[0].external_event_id
    second = await service.sync(CONNECTION)

    assert first.synced == second.synced == 1
    assert len(provider.events) == 1
    assert repository.records[0].external_event_id == first_id
    assert provider.events[first_id]["description"] == "Synthetic shift truth"


async def test_revoked_token_marks_connection_without_touching_shift_record() -> None:
    repository = FakeCalendarRepository()
    original = repository.records[0]
    service = CalendarService(
        repository,
        FakeProvider(refresh_failure=GoogleTokenRevokedError("CALENDAR_AUTH_REVOKED")),
        repository.box,
    )

    with pytest.raises(CalendarServiceError, match="CALENDAR_AUTH_REVOKED"):
        await service.sync(CONNECTION)

    assert repository.connection.status == "revoked"
    assert repository.records[0] == original


async def test_corrupt_encrypted_token_fails_with_safe_code() -> None:
    repository = FakeCalendarRepository()
    repository.connection = replace(
        repository.connection, encrypted_refresh_token="not-a-valid-ciphertext"
    )

    with pytest.raises(CalendarServiceError, match="CALENDAR_TOKEN_INVALID"):
        await CalendarService(repository, FakeProvider(), repository.box).sync(
            CONNECTION
        )


async def test_provider_failure_is_retryable_and_shift_truth_is_unchanged() -> None:
    repository = FakeCalendarRepository()
    provider = FakeProvider(event_failure=GoogleCalendarError("CALENDAR_UNAVAILABLE"))
    service = CalendarService(repository, provider, repository.box)
    original = repository.records[0]

    result = await service.sync(CONNECTION)

    assert result.failed == 1
    assert repository.records[0].retry_count == 1
    assert repository.records[0].shift_id == original.shift_id
    assert repository.records[0].start_at == original.start_at


async def test_deleted_shift_removes_external_event_without_shift_truth() -> None:
    repository = FakeCalendarRepository()
    repository.records = [
        replace(
            repository.records[0],
            shift_id=None,
            external_event_id="shiftmatesyntheticexternalid",
            status="pending_delete",
            start_at=None,
            end_at=None,
            shift_type=None,
            notes=None,
        )
    ]
    provider = FakeProvider()

    result = await CalendarService(repository, provider, repository.box).sync(
        CONNECTION
    )

    assert result.deleted == 1
    assert provider.deleted == ["shiftmatesyntheticexternalid"]
    assert repository.records[0].status == "deleted"

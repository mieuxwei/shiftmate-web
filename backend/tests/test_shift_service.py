from datetime import UTC, date, datetime
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import Connection

from backend.app.repositories.shifts import NewShift, ShiftRecord
from backend.app.services.shifts import (
    CreateShiftCommand,
    ProfileNotFoundError,
    ShiftNotFoundError,
    ShiftService,
    ShiftServiceError,
    UpdateShiftCommand,
)


class FakeShiftRepository:
    def __init__(self, timezone: str | None = "Asia/Taipei") -> None:
        self.timezone = timezone
        self.created: NewShift | None = None
        self.current: ShiftRecord | None = None

    def list_ids(self, connection: Connection) -> list[UUID]:
        return []

    def get_profile_timezone(self, connection: Connection) -> str | None:
        return self.timezone

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftRecord]:
        return [self.current] if self.current is not None else []

    def get_shift(self, connection: Connection, shift_id: UUID) -> ShiftRecord | None:
        if self.current is not None and self.current.id == shift_id:
            return self.current
        return None

    def create_shift(self, connection: Connection, new_shift: NewShift) -> ShiftRecord:
        self.created = new_shift
        now = datetime(2026, 9, 2, tzinfo=UTC)
        self.current = ShiftRecord(
            id=UUID("00000000-0000-0000-0000-000000000301"),
            work_date=new_shift.work_date,
            start_at=new_shift.start_at,
            end_at=new_shift.end_at,
            break_minutes=new_shift.break_minutes,
            shift_type=new_shift.shift_type,
            notes=new_shift.notes,
            source="manual",
            created_at=now,
            updated_at=now,
        )
        return self.current

    def update_shift(
        self, connection: Connection, shift_id: UUID, shift: NewShift
    ) -> ShiftRecord | None:
        if self.current is None or self.current.id != shift_id:
            return None
        self.current = ShiftRecord(
            id=shift_id,
            work_date=shift.work_date,
            start_at=shift.start_at,
            end_at=shift.end_at,
            break_minutes=shift.break_minutes,
            shift_type=shift.shift_type,
            notes=shift.notes,
            source=self.current.source,
            created_at=self.current.created_at,
            updated_at=datetime(2026, 9, 3, tzinfo=UTC),
        )
        return self.current

    def delete_shift(self, connection: Connection, shift_id: UUID) -> bool:
        if self.current is None or self.current.id != shift_id:
            return False
        self.current = None
        return True


CONNECTION = cast(Connection, object())


def test_create_uses_profile_timezone_to_derive_work_date() -> None:
    repository = FakeShiftRepository()
    service = ShiftService(repository)

    record = service.create_shift(
        CONNECTION,
        CreateShiftCommand(
            start_at=datetime(2026, 9, 2, 16, 30, tzinfo=UTC),
            end_at=datetime(2026, 9, 2, 18, 30, tzinfo=UTC),
            break_minutes=15,
            shift_type="night",
            notes="Synthetic shift",
        ),
    )

    assert record.work_date == date(2026, 9, 3)
    assert repository.created is not None
    assert repository.created.work_date == date(2026, 9, 3)


def test_create_rejects_invalid_domain_input_or_missing_profile() -> None:
    service = ShiftService(FakeShiftRepository())
    with pytest.raises(ShiftServiceError, match="after shift start"):
        service.create_shift(
            CONNECTION,
            CreateShiftCommand(
                start_at=datetime(2026, 9, 2, 10, tzinfo=UTC),
                end_at=datetime(2026, 9, 2, 9, tzinfo=UTC),
                break_minutes=0,
                shift_type="day",
                notes=None,
            ),
        )

    with pytest.raises(ProfileNotFoundError):
        ShiftService(FakeShiftRepository(timezone=None)).create_shift(
            CONNECTION,
            CreateShiftCommand(
                start_at=datetime(2026, 9, 2, 9, tzinfo=UTC),
                end_at=datetime(2026, 9, 2, 10, tzinfo=UTC),
                break_minutes=0,
                shift_type="day",
                notes=None,
            ),
        )


def test_list_rejects_reversed_date_range() -> None:
    service = ShiftService(FakeShiftRepository())

    with pytest.raises(ShiftServiceError, match="date_to cannot be before"):
        service.list_shifts(
            CONNECTION, date_from=date(2026, 9, 3), date_to=date(2026, 9, 2)
        )


def test_update_merges_fields_revalidates_and_allows_clearing_notes() -> None:
    repository = FakeShiftRepository()
    service = ShiftService(repository)
    created = service.create_shift(
        CONNECTION,
        CreateShiftCommand(
            start_at=datetime(2026, 9, 2, 16, 30, tzinfo=UTC),
            end_at=datetime(2026, 9, 2, 18, 30, tzinfo=UTC),
            break_minutes=15,
            shift_type="night",
            notes="Synthetic shift",
        ),
    )

    updated = service.update_shift(
        CONNECTION,
        created.id,
        UpdateShiftCommand(
            start_at=datetime(2026, 9, 3, 16, 30, tzinfo=UTC),
            end_at=datetime(2026, 9, 3, 19, 0, tzinfo=UTC),
            notes=None,
            notes_supplied=True,
        ),
    )

    assert updated.work_date == date(2026, 9, 4)
    assert updated.break_minutes == 15
    assert updated.shift_type == "night"
    assert updated.notes is None


def test_update_and_delete_hide_missing_shifts() -> None:
    service = ShiftService(FakeShiftRepository())
    missing_id = UUID("00000000-0000-0000-0000-000000000399")

    with pytest.raises(ShiftNotFoundError):
        service.update_shift(CONNECTION, missing_id, UpdateShiftCommand(notes="x"))
    with pytest.raises(ShiftNotFoundError):
        service.delete_shift(CONNECTION, missing_id)

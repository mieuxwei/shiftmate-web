from dataclasses import dataclass
from datetime import date, datetime
from uuid import UUID

from sqlalchemy import Connection

from backend.app.domain.schedule import ScheduleValidationError, Shift
from backend.app.repositories.shifts import NewShift, ShiftRecord, ShiftRepository


class ShiftServiceError(ValueError):
    """Raised when a shift operation cannot be completed."""


class ProfileNotFoundError(ShiftServiceError):
    """Raised when the authenticated user has no profile."""


class ShiftNotFoundError(ShiftServiceError):
    """Raised when a shift is missing or hidden by owner isolation."""


@dataclass(frozen=True, slots=True)
class CreateShiftCommand:
    start_at: datetime
    end_at: datetime
    break_minutes: int
    shift_type: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class UpdateShiftCommand:
    start_at: datetime | None = None
    end_at: datetime | None = None
    break_minutes: int | None = None
    shift_type: str | None = None
    notes: str | None = None
    notes_supplied: bool = False


class ShiftService:
    def __init__(self, repository: ShiftRepository) -> None:
        self.repository = repository

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> list[ShiftRecord]:
        if date_from is not None and date_to is not None and date_to < date_from:
            raise ShiftServiceError("date_to cannot be before date_from")
        return list(self.repository.list_shifts(connection, date_from, date_to))

    def create_shift(
        self, connection: Connection, command: CreateShiftCommand
    ) -> ShiftRecord:
        timezone = self.repository.get_profile_timezone(connection)
        if timezone is None:
            raise ProfileNotFoundError("Authenticated user profile was not found")

        try:
            shift = Shift(
                start_at=command.start_at,
                end_at=command.end_at,
                break_minutes=command.break_minutes,
                timezone=timezone,
                shift_type=command.shift_type,
            )
        except ScheduleValidationError as error:
            raise ShiftServiceError(str(error)) from error

        return self.repository.create_shift(
            connection,
            NewShift(
                work_date=shift.work_date,
                start_at=shift.start_at,
                end_at=shift.end_at,
                break_minutes=shift.break_minutes,
                shift_type=shift.shift_type,
                notes=command.notes,
            ),
        )

    def update_shift(
        self, connection: Connection, shift_id: UUID, command: UpdateShiftCommand
    ) -> ShiftRecord:
        existing = self.repository.get_shift(connection, shift_id)
        if existing is None:
            raise ShiftNotFoundError("Shift was not found")

        timezone = self.repository.get_profile_timezone(connection)
        if timezone is None:
            raise ProfileNotFoundError("Authenticated user profile was not found")

        try:
            shift = Shift(
                start_at=command.start_at or existing.start_at,
                end_at=command.end_at or existing.end_at,
                break_minutes=(
                    command.break_minutes
                    if command.break_minutes is not None
                    else existing.break_minutes
                ),
                timezone=timezone,
                shift_type=command.shift_type or existing.shift_type,
            )
        except ScheduleValidationError as error:
            raise ShiftServiceError(str(error)) from error

        updated = self.repository.update_shift(
            connection,
            shift_id,
            NewShift(
                work_date=shift.work_date,
                start_at=shift.start_at,
                end_at=shift.end_at,
                break_minutes=shift.break_minutes,
                shift_type=shift.shift_type,
                notes=command.notes if command.notes_supplied else existing.notes,
            ),
        )
        if updated is None:
            raise ShiftNotFoundError("Shift was not found")
        return updated

    def delete_shift(self, connection: Connection, shift_id: UUID) -> None:
        if not self.repository.delete_shift(connection, shift_id):
            raise ShiftNotFoundError("Shift was not found")

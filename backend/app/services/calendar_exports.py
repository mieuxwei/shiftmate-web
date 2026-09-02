from dataclasses import dataclass
from datetime import date

from sqlalchemy import Connection

from backend.app.repositories.shifts import ShiftRepository
from backend.app.services.ics import export_shifts_to_ics


class CalendarExportError(ValueError):
    """Raised when a calendar export request is invalid."""


@dataclass(frozen=True, slots=True)
class CalendarExport:
    filename: str
    media_type: str
    content: bytes


class CalendarExportService:
    """Create a read-only ICS export from owner-scoped shift records."""

    def __init__(self, shift_repository: ShiftRepository) -> None:
        self.shift_repository = shift_repository

    def create_export(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> CalendarExport:
        if date_from and date_to and date_to < date_from:
            raise CalendarExportError("CALENDAR_DATE_RANGE_INVALID")
        shifts = self.shift_repository.list_shifts(connection, date_from, date_to)
        return CalendarExport(
            filename="shiftmate-schedule.ics",
            media_type="text/calendar; charset=utf-8",
            content=export_shifts_to_ics(shifts, date_from, date_to),
        )

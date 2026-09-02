from datetime import UTC, date, datetime
from uuid import UUID

from backend.app.repositories.shifts import ShiftRecord
from backend.app.services.ics import export_shifts_to_ics


def test_ics_export_is_stable_escaped_folded_and_uses_utc() -> None:
    shift = ShiftRecord(
        id=UUID("00000000-0000-0000-0000-000000000702"),
        work_date=date(2026, 9, 2),
        start_at=datetime(2026, 9, 2, 1, tzinfo=UTC),
        end_at=datetime(2026, 9, 2, 9, tzinfo=UTC),
        break_minutes=30,
        shift_type="day",
        notes="Synthetic, safe; note\n" + "長" * 40,
        source="manual",
        created_at=datetime(2026, 9, 1, tzinfo=UTC),
        updated_at=datetime(2026, 9, 1, tzinfo=UTC),
    )

    content = export_shifts_to_ics([shift], date(2026, 9, 1), date(2026, 9, 30))
    text = content.decode()

    assert text.startswith("BEGIN:VCALENDAR\r\nVERSION:2.0\r\n")
    assert "UID:00000000-0000-0000-0000-000000000702@shiftmate.local" in text
    assert "DTSTART:20260902T010000Z" in text
    assert "Synthetic\\, safe\\; note\\n" in text.replace("\r\n ", "")
    assert text.endswith("END:VCALENDAR\r\n")
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))

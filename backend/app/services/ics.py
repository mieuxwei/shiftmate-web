from collections.abc import Sequence
from datetime import UTC, date, datetime

from backend.app.repositories.shifts import ShiftRecord


def export_shifts_to_ics(
    shifts: Sequence[ShiftRecord], date_from: date | None, date_to: date | None
) -> bytes:
    calendar_name = "ShiftMate schedule"
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//ShiftMate Web//Schedule Export//EN",
        "CALSCALE:GREGORIAN",
        f"X-WR-CALNAME:{_escape(calendar_name)}",
    ]
    for shift in shifts:
        lines.extend(
            [
                "BEGIN:VEVENT",
                f"UID:{shift.id}@shiftmate.local",
                f"DTSTAMP:{_utc_value(shift.updated_at)}",
                f"DTSTART:{_utc_value(shift.start_at)}",
                f"DTEND:{_utc_value(shift.end_at)}",
                f"SUMMARY:{_escape(f'Shift · {shift.shift_type}')}",
                f"DESCRIPTION:{_escape(_description(shift))}",
                "END:VEVENT",
            ]
        )
    if date_from or date_to:
        range_text = f"{date_from or ''}/{date_to or ''}"
        lines.insert(5, f"X-SHIFTMATE-RANGE:{range_text}")
    lines.append("END:VCALENDAR")
    folded = [part for line in lines for part in _fold_line(line)]
    return ("\r\n".join(folded) + "\r\n").encode()


def _description(shift: ShiftRecord) -> str:
    parts = [f"Break: {shift.break_minutes} minutes"]
    if shift.notes:
        parts.append(shift.notes)
    return "\n".join(parts)


def _utc_value(value: datetime) -> str:
    return value.astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


def _escape(value: str) -> str:
    return (
        value.replace("\\", "\\\\")
        .replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\\n")
        .replace(";", "\\;")
        .replace(",", "\\,")
    )


def _fold_line(value: str) -> list[str]:
    parts: list[str] = []
    current = ""
    byte_limit = 75
    for character in value:
        if len((current + character).encode()) > byte_limit:
            parts.append(current)
            current = " " + character
            byte_limit = 75
        else:
            current += character
    parts.append(current)
    return parts

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol
from uuid import UUID

from sqlalchemy import Connection, RowMapping, text


@dataclass(frozen=True, slots=True)
class NewShift:
    work_date: date
    start_at: datetime
    end_at: datetime
    break_minutes: int
    shift_type: str
    notes: str | None


@dataclass(frozen=True, slots=True)
class ShiftRecord:
    id: UUID
    work_date: date
    start_at: datetime
    end_at: datetime
    break_minutes: int
    shift_type: str
    notes: str | None
    source: str
    created_at: datetime
    updated_at: datetime


class ShiftRepository(Protocol):
    def list_ids(self, connection: Connection) -> list[UUID]: ...

    def get_profile_timezone(self, connection: Connection) -> str | None: ...

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Sequence[ShiftRecord]: ...

    def get_shift(
        self, connection: Connection, shift_id: UUID
    ) -> ShiftRecord | None: ...

    def create_shift(
        self, connection: Connection, new_shift: NewShift
    ) -> ShiftRecord: ...

    def update_shift(
        self, connection: Connection, shift_id: UUID, shift: NewShift
    ) -> ShiftRecord | None: ...

    def delete_shift(self, connection: Connection, shift_id: UUID) -> bool: ...


class PostgresShiftRepository:
    _shift_columns = """
        id, work_date, start_at, end_at, break_minutes, shift_type,
        notes, source, created_at, updated_at
    """

    def list_ids(self, connection: Connection) -> list[UUID]:
        rows = connection.execute(text("SELECT id FROM shifts ORDER BY id"))
        return [row.id for row in rows]

    def get_profile_timezone(self, connection: Connection) -> str | None:
        return connection.execute(
            text("SELECT timezone FROM profiles")
        ).scalar_one_or_none()

    def list_shifts(
        self,
        connection: Connection,
        date_from: date | None = None,
        date_to: date | None = None,
    ) -> Sequence[ShiftRecord]:
        conditions: list[str] = []
        parameters: dict[str, date] = {}
        if date_from is not None:
            conditions.append("work_date >= :date_from")
            parameters["date_from"] = date_from
        if date_to is not None:
            conditions.append("work_date <= :date_to")
            parameters["date_to"] = date_to
        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        rows = connection.execute(
            text(
                f"""
                SELECT {self._shift_columns}
                FROM shifts
                {where_clause}
                ORDER BY start_at, id
                """
            ),
            parameters,
        )
        return [_to_record(row._mapping) for row in rows]

    def get_shift(self, connection: Connection, shift_id: UUID) -> ShiftRecord | None:
        row = connection.execute(
            text(
                f"""
                SELECT {self._shift_columns}
                FROM shifts
                WHERE id = :shift_id
                """
            ),
            {"shift_id": shift_id},
        ).one_or_none()
        return _to_record(row._mapping) if row is not None else None

    def create_shift(self, connection: Connection, new_shift: NewShift) -> ShiftRecord:
        row = connection.execute(
            text(
                f"""
                INSERT INTO shifts (
                    owner_id, work_date, start_at, end_at, break_minutes,
                    shift_type, notes, source
                )
                VALUES (
                    app_private.current_user_id(), :work_date, :start_at,
                    :end_at, :break_minutes, :shift_type, :notes, 'manual'
                )
                RETURNING {self._shift_columns}
                """
            ),
            {
                "work_date": new_shift.work_date,
                "start_at": new_shift.start_at,
                "end_at": new_shift.end_at,
                "break_minutes": new_shift.break_minutes,
                "shift_type": new_shift.shift_type,
                "notes": new_shift.notes,
            },
        ).one()
        return _to_record(row._mapping)

    def update_shift(
        self, connection: Connection, shift_id: UUID, shift: NewShift
    ) -> ShiftRecord | None:
        row = connection.execute(
            text(
                f"""
                UPDATE shifts
                SET work_date = :work_date,
                    start_at = :start_at,
                    end_at = :end_at,
                    break_minutes = :break_minutes,
                    shift_type = :shift_type,
                    notes = :notes,
                    updated_at = now()
                WHERE id = :shift_id
                RETURNING {self._shift_columns}
                """
            ),
            {
                "shift_id": shift_id,
                "work_date": shift.work_date,
                "start_at": shift.start_at,
                "end_at": shift.end_at,
                "break_minutes": shift.break_minutes,
                "shift_type": shift.shift_type,
                "notes": shift.notes,
            },
        ).one_or_none()
        return _to_record(row._mapping) if row is not None else None

    def delete_shift(self, connection: Connection, shift_id: UUID) -> bool:
        connection.execute(
            text(
                """
                UPDATE calendar_sync_records
                SET status = 'pending_delete',
                    last_error_code = NULL,
                    updated_at = now()
                WHERE shift_id = :shift_id
                  AND status <> 'deleted'
                """
            ),
            {"shift_id": shift_id},
        )
        deleted_id = connection.execute(
            text("DELETE FROM shifts WHERE id = :shift_id RETURNING id"),
            {"shift_id": shift_id},
        ).scalar_one_or_none()
        return deleted_id is not None


def _to_record(row: RowMapping) -> ShiftRecord:
    return ShiftRecord(
        id=row["id"],
        work_date=row["work_date"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        break_minutes=row["break_minutes"],
        shift_type=row["shift_type"],
        notes=row["notes"],
        source=row["source"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )

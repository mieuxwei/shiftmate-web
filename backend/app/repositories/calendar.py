import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Literal, Protocol, cast
from uuid import UUID

from sqlalchemy import Connection, RowMapping, text

CalendarConnectionStatus = Literal["active", "revoked", "error"]


@dataclass(frozen=True, slots=True)
class CalendarConnectionRecord:
    owner_id: UUID
    encrypted_refresh_token: str
    scopes: tuple[str, ...]
    expires_at: datetime | None
    status: CalendarConnectionStatus


@dataclass(frozen=True, slots=True)
class CalendarSyncRecord:
    id: UUID
    owner_id: UUID
    shift_id: UUID | None
    external_event_id: str | None
    status: str
    retry_count: int
    start_at: datetime | None
    end_at: datetime | None
    shift_type: str | None
    notes: str | None


class CalendarRepository(Protocol):
    def get_connection(
        self, connection: Connection, *, for_update: bool = False
    ) -> CalendarConnectionRecord | None: ...

    def save_connection(
        self,
        connection: Connection,
        encrypted_refresh_token: str | None,
        scopes: Sequence[str],
        expires_at: datetime | None,
    ) -> CalendarConnectionRecord: ...

    def mark_connection_revoked(self, connection: Connection) -> None: ...

    def ensure_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> None: ...

    def list_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> Sequence[CalendarSyncRecord]: ...

    def mark_sync_success(
        self,
        connection: Connection,
        record_id: UUID,
        event_id: str | None,
        deleted: bool,
    ) -> None: ...

    def mark_sync_failure(
        self, connection: Connection, record_id: UUID, error_code: str
    ) -> None: ...


class PostgresCalendarRepository:
    def get_connection(
        self, connection: Connection, *, for_update: bool = False
    ) -> CalendarConnectionRecord | None:
        lock = "FOR UPDATE" if for_update else ""
        row = connection.execute(
            text(
                f"""
                SELECT owner_id, encrypted_refresh_token, scopes, expires_at, status
                FROM calendar_connections
                ORDER BY created_at DESC
                LIMIT 1
                {lock}
                """
            )
        ).one_or_none()
        return _connection_record(row._mapping) if row is not None else None

    def save_connection(
        self,
        connection: Connection,
        encrypted_refresh_token: str | None,
        scopes: Sequence[str],
        expires_at: datetime | None,
    ) -> CalendarConnectionRecord:
        if encrypted_refresh_token is None:
            row = connection.execute(
                text(
                    """
                    UPDATE calendar_connections
                    SET scopes = CAST(:scopes AS jsonb),
                        expires_at = :expires_at,
                        status = 'active', revoked_at = NULL, updated_at = now()
                    RETURNING owner_id, encrypted_refresh_token, scopes,
                              expires_at, status
                    """
                ),
                {
                    "scopes": json.dumps(list(scopes)),
                    "expires_at": expires_at,
                },
            ).one()
            return _connection_record(row._mapping)
        row = connection.execute(
            text(
                """
                INSERT INTO calendar_connections (
                    owner_id, encrypted_refresh_token, scopes, expires_at, status
                )
                VALUES (
                    app_private.current_user_id(), :token,
                    CAST(:scopes AS jsonb), :expires_at, 'active'
                )
                ON CONFLICT (owner_id) DO UPDATE
                SET encrypted_refresh_token = COALESCE(
                        EXCLUDED.encrypted_refresh_token,
                        calendar_connections.encrypted_refresh_token
                    ),
                    scopes = EXCLUDED.scopes,
                    expires_at = EXCLUDED.expires_at,
                    status = 'active',
                    revoked_at = NULL,
                    updated_at = now()
                RETURNING owner_id, encrypted_refresh_token, scopes,
                          expires_at, status
                """
            ),
            {
                "token": encrypted_refresh_token,
                "scopes": json.dumps(list(scopes)),
                "expires_at": expires_at,
            },
        ).one()
        return _connection_record(row._mapping)

    def mark_connection_revoked(self, connection: Connection) -> None:
        connection.execute(
            text(
                """
                UPDATE calendar_connections
                SET status = 'revoked', revoked_at = now(), updated_at = now()
                """
            )
        )

    def ensure_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> None:
        where, parameters = _date_filter(date_from, date_to, "shifts")
        connection.execute(
            text(
                f"""
                INSERT INTO calendar_sync_records (owner_id, shift_id, status)
                SELECT owner_id, id, 'pending'
                FROM shifts
                {where}
                ON CONFLICT (owner_id, shift_id) DO NOTHING
                """
            ),
            parameters,
        )

    def list_sync_records(
        self,
        connection: Connection,
        date_from: date | None,
        date_to: date | None,
    ) -> Sequence[CalendarSyncRecord]:
        where, parameters = _date_filter(date_from, date_to, "shift_row")
        range_condition = f"({where.removeprefix('WHERE ')} OR record.shift_id IS NULL)"
        rows = connection.execute(
            text(
                f"""
                SELECT record.id, record.owner_id, record.shift_id,
                       record.external_event_id, record.status, record.retry_count,
                       shift_row.start_at, shift_row.end_at,
                       shift_row.shift_type, shift_row.notes
                FROM calendar_sync_records AS record
                LEFT JOIN shifts AS shift_row ON shift_row.id = record.shift_id
                WHERE record.status <> 'deleted' AND {range_condition}
                ORDER BY record.created_at, record.id
                """
            ),
            parameters,
        )
        return [_sync_record(row._mapping) for row in rows]

    def mark_sync_success(
        self,
        connection: Connection,
        record_id: UUID,
        event_id: str | None,
        deleted: bool,
    ) -> None:
        connection.execute(
            text(
                """
                UPDATE calendar_sync_records
                SET external_event_id = :event_id,
                    status = :status,
                    last_error_code = NULL,
                    updated_at = now()
                WHERE id = :record_id
                """
            ),
            {
                "record_id": record_id,
                "event_id": event_id,
                "status": "deleted" if deleted else "synced",
            },
        )

    def mark_sync_failure(
        self, connection: Connection, record_id: UUID, error_code: str
    ) -> None:
        connection.execute(
            text(
                """
                UPDATE calendar_sync_records
                SET status = 'failed', last_error_code = :error_code,
                    retry_count = retry_count + 1, updated_at = now()
                WHERE id = :record_id
                """
            ),
            {"record_id": record_id, "error_code": error_code},
        )


def _date_filter(
    date_from: date | None, date_to: date | None, alias: str
) -> tuple[str, dict[str, date]]:
    conditions: list[str] = []
    parameters: dict[str, date] = {}
    if date_from is not None:
        conditions.append(f"{alias}.work_date >= :date_from")
        parameters["date_from"] = date_from
    if date_to is not None:
        conditions.append(f"{alias}.work_date <= :date_to")
        parameters["date_to"] = date_to
    where = "WHERE " + " AND ".join(conditions) if conditions else "WHERE TRUE"
    return where, parameters


def _connection_record(row: RowMapping) -> CalendarConnectionRecord:
    return CalendarConnectionRecord(
        owner_id=row["owner_id"],
        encrypted_refresh_token=row["encrypted_refresh_token"],
        scopes=tuple(row["scopes"]),
        expires_at=row["expires_at"],
        status=cast(CalendarConnectionStatus, row["status"]),
    )


def _sync_record(row: RowMapping) -> CalendarSyncRecord:
    return CalendarSyncRecord(
        id=row["id"],
        owner_id=row["owner_id"],
        shift_id=row["shift_id"],
        external_event_id=row["external_event_id"],
        status=row["status"],
        retry_count=row["retry_count"],
        start_at=row["start_at"],
        end_at=row["end_at"],
        shift_type=row["shift_type"],
        notes=row["notes"],
    )

import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import Connection, RowMapping, text


@dataclass(frozen=True, slots=True)
class NewImport:
    filename: str
    media_type: str
    sha256: str


@dataclass(frozen=True, slots=True)
class NewImportItem:
    raw_payload: dict[str, object]
    work_date: date | None
    start_at: datetime | None
    end_at: datetime | None
    break_minutes: int | None
    shift_type: str | None
    notes: str | None
    validation_status: str
    warnings: list[str]


@dataclass(frozen=True, slots=True)
class ImportItemRecord:
    id: UUID
    work_date: date | None
    start_at: datetime | None
    end_at: datetime | None
    break_minutes: int | None
    shift_type: str | None
    notes: str | None
    validation_status: str
    needs_review: bool
    warnings: list[str]
    confirmed: bool
    committed_shift_id: UUID | None


@dataclass(frozen=True, slots=True)
class ImportRecord:
    id: UUID
    filename: str
    media_type: str
    status: str
    model_name: str | None
    prompt_version: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    items: Sequence[ImportItemRecord]


class ImportRepository(Protocol):
    def get_profile_timezone(self, connection: Connection) -> str | None: ...
    def create_import(self, connection: Connection, new_import: NewImport) -> UUID: ...
    def set_extracting(
        self, connection: Connection, import_id: UUID, model: str, prompt: str
    ) -> None: ...
    def save_extraction(
        self, connection: Connection, import_id: UUID, items: Sequence[NewImportItem]
    ) -> None: ...
    def set_failed(
        self, connection: Connection, import_id: UUID, code: str
    ) -> None: ...
    def get_import(
        self, connection: Connection, import_id: UUID
    ) -> ImportRecord | None: ...
    def update_item(
        self,
        connection: Connection,
        import_id: UUID,
        item_id: UUID,
        item: NewImportItem,
        confirmed: bool,
    ) -> bool: ...
    def commit(self, connection: Connection, import_id: UUID) -> list[UUID] | None: ...


class PostgresImportRepository:
    def get_profile_timezone(self, connection: Connection) -> str | None:
        return cast(
            str | None,
            connection.execute(
                text("SELECT timezone FROM profiles")
            ).scalar_one_or_none(),
        )

    def create_import(self, connection: Connection, new_import: NewImport) -> UUID:
        return cast(
            UUID,
            connection.execute(
                text(
                    """
                    INSERT INTO shift_imports (owner_id, filename, media_type, sha256)
                    VALUES (
                        app_private.current_user_id(), :filename,
                        :media_type, :sha256
                    )
                    RETURNING id
                    """
                ),
                {
                    "filename": new_import.filename,
                    "media_type": new_import.media_type,
                    "sha256": new_import.sha256,
                },
            ).scalar_one(),
        )

    def set_extracting(
        self, connection: Connection, import_id: UUID, model: str, prompt: str
    ) -> None:
        connection.execute(
            text(
                """
                UPDATE shift_imports
                SET status = 'extracting', model_name = :model,
                    prompt_version = :prompt, error_code = NULL, updated_at = now()
                WHERE id = :import_id AND status IN ('uploaded', 'failed')
                """
            ),
            {"import_id": import_id, "model": model, "prompt": prompt},
        )

    def save_extraction(
        self, connection: Connection, import_id: UUID, items: Sequence[NewImportItem]
    ) -> None:
        connection.execute(
            text("DELETE FROM shift_import_items WHERE import_id = :import_id"),
            {"import_id": import_id},
        )
        for item_index, item in enumerate(items):
            connection.execute(
                text(
                    """
                    INSERT INTO shift_import_items (
                        import_id, owner_id, item_index, raw_payload,
                        normalized_work_date,
                        normalized_start_at, normalized_end_at,
                        normalized_break_minutes, normalized_shift_type,
                        normalized_notes, validation_status, warnings
                    ) VALUES (
                        :import_id, app_private.current_user_id(), :item_index,
                        CAST(:raw_payload AS jsonb), :work_date, :start_at, :end_at,
                        :break_minutes, :shift_type, :notes, :validation_status,
                        CAST(:warnings AS jsonb)
                    )
                    """
                ),
                {
                    "import_id": import_id,
                    "item_index": item_index,
                    "raw_payload": json.dumps(item.raw_payload),
                    "work_date": item.work_date,
                    "start_at": item.start_at,
                    "end_at": item.end_at,
                    "break_minutes": item.break_minutes,
                    "shift_type": item.shift_type,
                    "notes": item.notes,
                    "validation_status": item.validation_status,
                    "warnings": json.dumps(item.warnings),
                },
            )
        connection.execute(
            text(
                """
                UPDATE shift_imports SET status = 'review', updated_at = now()
                WHERE id = :import_id AND status = 'extracting'
                """
            ),
            {"import_id": import_id},
        )

    def set_failed(self, connection: Connection, import_id: UUID, code: str) -> None:
        connection.execute(
            text(
                """
                UPDATE shift_imports
                SET status = 'failed', error_code = :code, updated_at = now()
                WHERE id = :import_id AND status = 'extracting'
                """
            ),
            {"import_id": import_id, "code": code},
        )

    def get_import(
        self, connection: Connection, import_id: UUID
    ) -> ImportRecord | None:
        row = connection.execute(
            text(
                """
                SELECT id, filename, media_type, status, model_name,
                       prompt_version, error_code, created_at, updated_at
                FROM shift_imports WHERE id = :import_id
                """
            ),
            {"import_id": import_id},
        ).one_or_none()
        if row is None:
            return None
        items = connection.execute(
            text(
                """
                SELECT id, normalized_work_date, normalized_start_at,
                       normalized_end_at, normalized_break_minutes,
                       normalized_shift_type, normalized_notes, validation_status,
                       (raw_payload->>'needs_review')::boolean AS needs_review,
                       warnings, confirmed_at IS NOT NULL AS confirmed,
                       committed_shift_id
                FROM shift_import_items
                WHERE import_id = :import_id ORDER BY item_index
                """
            ),
            {"import_id": import_id},
        )
        return _to_import(row._mapping, [_to_item(item._mapping) for item in items])

    def update_item(
        self,
        connection: Connection,
        import_id: UUID,
        item_id: UUID,
        item: NewImportItem,
        confirmed: bool,
    ) -> bool:
        updated = connection.execute(
            text(
                """
                UPDATE shift_import_items
                SET normalized_work_date = :work_date,
                    normalized_start_at = :start_at,
                    normalized_end_at = :end_at,
                    normalized_break_minutes = :break_minutes,
                    normalized_shift_type = :shift_type,
                    normalized_notes = :notes,
                    validation_status = :validation_status,
                    warnings = CAST(:warnings AS jsonb),
                    confirmed_at = CASE WHEN :confirmed THEN now() ELSE NULL END,
                    updated_at = now()
                WHERE id = :item_id AND import_id = :import_id
                  AND committed_shift_id IS NULL
                RETURNING id
                """
            ),
            {
                "import_id": import_id,
                "item_id": item_id,
                "work_date": item.work_date,
                "start_at": item.start_at,
                "end_at": item.end_at,
                "break_minutes": item.break_minutes,
                "shift_type": item.shift_type,
                "notes": item.notes,
                "validation_status": item.validation_status,
                "warnings": json.dumps(item.warnings),
                "confirmed": confirmed,
            },
        ).scalar_one_or_none()
        return updated is not None

    def commit(self, connection: Connection, import_id: UUID) -> list[UUID] | None:
        state = connection.execute(
            text("SELECT status FROM shift_imports WHERE id = :id FOR UPDATE"),
            {"id": import_id},
        ).scalar_one_or_none()
        if state is None:
            return None
        existing = list(
            connection.execute(
                text(
                    """
                    SELECT committed_shift_id FROM shift_import_items
                    WHERE import_id = :id AND committed_shift_id IS NOT NULL
                    ORDER BY item_index
                    """
                ),
                {"id": import_id},
            ).scalars()
        )
        if state == "committed":
            return existing
        rows = connection.execute(
            text(
                """
                SELECT id, normalized_work_date AS work_date,
                       normalized_start_at AS start_at,
                       normalized_end_at AS end_at,
                       normalized_break_minutes AS break_minutes,
                       normalized_shift_type AS shift_type,
                       normalized_notes AS notes
                FROM shift_import_items
                WHERE import_id = :id AND confirmed_at IS NOT NULL
                  AND validation_status = 'valid' AND committed_shift_id IS NULL
                ORDER BY item_index FOR UPDATE
                """
            ),
            {"id": import_id},
        ).mappings()
        created = existing
        for row in rows:
            shift_id = connection.execute(
                text(
                    """
                    INSERT INTO shifts (
                        owner_id, work_date, start_at, end_at, break_minutes,
                        shift_type, notes, source
                    ) VALUES (
                        app_private.current_user_id(), :work_date, :start_at,
                        :end_at, :break_minutes, :shift_type, :notes, 'import'
                    ) RETURNING id
                    """
                ),
                dict(row),
            ).scalar_one()
            connection.execute(
                text(
                    "UPDATE shift_import_items SET committed_shift_id = :shift_id "
                    "WHERE id = :item_id"
                ),
                {"shift_id": shift_id, "item_id": row["id"]},
            )
            created.append(shift_id)
        connection.execute(
            text(
                "UPDATE shift_imports SET status = 'committed', updated_at = now() "
                "WHERE id = :id AND status = 'review'"
            ),
            {"id": import_id},
        )
        return created


def _to_item(row: RowMapping) -> ImportItemRecord:
    return ImportItemRecord(
        id=row["id"],
        work_date=row["normalized_work_date"],
        start_at=row["normalized_start_at"],
        end_at=row["normalized_end_at"],
        break_minutes=row["normalized_break_minutes"],
        shift_type=row["normalized_shift_type"],
        notes=row["normalized_notes"],
        validation_status=row["validation_status"],
        needs_review=bool(row["needs_review"]),
        warnings=list(row["warnings"]),
        confirmed=bool(row["confirmed"]),
        committed_shift_id=row["committed_shift_id"],
    )


def _to_import(row: RowMapping, items: Sequence[ImportItemRecord]) -> ImportRecord:
    return ImportRecord(
        id=row["id"],
        filename=row["filename"],
        media_type=row["media_type"],
        status=row["status"],
        model_name=row["model_name"],
        prompt_version=row["prompt_version"],
        error_code=row["error_code"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        items=items,
    )

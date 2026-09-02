from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy import Connection

from backend.app.domain.schedule import ScheduleValidationError, Shift
from backend.app.integrations.gemini import GeminiExtractionError, ScheduleExtractor
from backend.app.repositories.imports import (
    ImportRecord,
    ImportRepository,
    NewImport,
    NewImportItem,
)
from backend.app.schemas.imports import ExtractedShift, ImportItemUpdateRequest


class ImportServiceError(ValueError):
    """Safe import workflow error exposed by the transport adapter."""


class ImportNotFoundError(ImportServiceError):
    pass


class ImportConflictError(ImportServiceError):
    pass


@dataclass(frozen=True, slots=True)
class ValidatedUploadInfo:
    path: Path
    filename: str
    media_type: str
    sha256: str


class ImportService:
    def __init__(
        self, repository: ImportRepository, extractor: ScheduleExtractor | None = None
    ) -> None:
        self.repository = repository
        self.extractor = extractor

    def create_and_extract(
        self, connection: Connection, upload: ValidatedUploadInfo
    ) -> ImportRecord:
        import_id, timezone = self.create_draft(connection, upload)
        items, error_code = self.extract(upload, timezone)
        return self.complete_extraction(connection, import_id, items, error_code)

    def create_draft(
        self, connection: Connection, upload: ValidatedUploadInfo
    ) -> tuple[UUID, str]:
        if self.extractor is None:
            raise ImportServiceError("GEMINI_NOT_CONFIGURED")
        timezone = self.repository.get_profile_timezone(connection)
        if timezone is None:
            raise ImportNotFoundError("PROFILE_NOT_FOUND")
        import_id = self.repository.create_import(
            connection,
            NewImport(
                filename=upload.filename,
                media_type=upload.media_type,
                sha256=upload.sha256,
            ),
        )
        self.repository.set_extracting(
            connection,
            import_id,
            self.extractor.model_name,
            self.extractor.prompt_version,
        )
        return import_id, timezone

    def extract(
        self, upload: ValidatedUploadInfo, timezone: str
    ) -> tuple[list[NewImportItem], str | None]:
        if self.extractor is None:
            raise ImportServiceError("GEMINI_NOT_CONFIGURED")
        try:
            extraction = self.extractor.extract(
                upload.path, upload.media_type, timezone
            )
        except GeminiExtractionError as error:
            return [], error.code
        return [_normalize_extracted(item, timezone) for item in extraction.items], None

    def complete_extraction(
        self,
        connection: Connection,
        import_id: UUID,
        items: list[NewImportItem],
        error_code: str | None,
    ) -> ImportRecord:
        if error_code is not None:
            self.repository.set_failed(connection, import_id, error_code)
        else:
            self.repository.save_extraction(connection, import_id, items)
        record = self.repository.get_import(connection, import_id)
        if record is None:
            raise ImportNotFoundError("IMPORT_NOT_FOUND")
        return record

    def get_import(self, connection: Connection, import_id: UUID) -> ImportRecord:
        record = self.repository.get_import(connection, import_id)
        if record is None:
            raise ImportNotFoundError("IMPORT_NOT_FOUND")
        return record

    def update_item(
        self,
        connection: Connection,
        import_id: UUID,
        item_id: UUID,
        patch: ImportItemUpdateRequest,
    ) -> ImportRecord:
        record = self.get_import(connection, import_id)
        if record.status != "review":
            raise ImportConflictError("IMPORT_NOT_REVIEWABLE")
        existing = next((item for item in record.items if item.id == item_id), None)
        if existing is None:
            raise ImportNotFoundError("IMPORT_ITEM_NOT_FOUND")
        timezone = self.repository.get_profile_timezone(connection)
        if timezone is None:
            raise ImportNotFoundError("PROFILE_NOT_FOUND")

        zone = ZoneInfo(timezone)
        local_start = existing.start_at.astimezone(zone) if existing.start_at else None
        local_end = existing.end_at.astimezone(zone) if existing.end_at else None
        fields = patch.model_fields_set
        work_date = patch.work_date if "work_date" in fields else existing.work_date
        start_time = (
            patch.start_time
            if "start_time" in fields
            else (local_start.timetz().replace(tzinfo=None) if local_start else None)
        )
        end_time = (
            patch.end_time
            if "end_time" in fields
            else (local_end.timetz().replace(tzinfo=None) if local_end else None)
        )
        current_crosses = bool(
            local_start and local_end and local_end.date() > local_start.date()
        )
        crosses_midnight = (
            patch.crosses_midnight if "crosses_midnight" in fields else current_crosses
        )
        break_minutes = (
            patch.break_minutes
            if "break_minutes" in fields
            else (existing.break_minutes or 0)
        )
        shift_type = (
            patch.shift_type
            if "shift_type" in fields
            else (existing.shift_type or "other")
        )
        if crosses_midnight is None or break_minutes is None or shift_type is None:
            raise ImportServiceError("IMPORT_ITEM_FIELDS_INVALID")
        candidate = ExtractedShift(
            work_date=work_date,
            start_time=start_time,
            end_time=end_time,
            crosses_midnight=crosses_midnight,
            break_minutes=break_minutes,
            shift_type=shift_type,
            notes=patch.notes if "notes" in fields else existing.notes,
            needs_review=False,
            warnings=[],
        )
        normalized = _normalize_extracted(candidate, timezone)
        confirmed = patch.confirmed if "confirmed" in fields else existing.confirmed
        if confirmed and normalized.validation_status != "valid":
            raise ImportConflictError("INVALID_ITEM_CANNOT_BE_CONFIRMED")
        if not self.repository.update_item(
            connection, import_id, item_id, normalized, bool(confirmed)
        ):
            raise ImportNotFoundError("IMPORT_ITEM_NOT_FOUND")
        return self.get_import(connection, import_id)

    def commit(self, connection: Connection, import_id: UUID) -> list[UUID]:
        record = self.get_import(connection, import_id)
        if record.status == "committed":
            return [
                item.committed_shift_id
                for item in record.items
                if item.committed_shift_id is not None
            ]
        if record.status != "review":
            raise ImportConflictError("IMPORT_NOT_COMMITTABLE")
        if not any(
            item.confirmed and item.validation_status == "valid"
            for item in record.items
        ):
            raise ImportConflictError("NO_CONFIRMED_ITEMS")
        created = self.repository.commit(connection, import_id)
        if created is None:
            raise ImportNotFoundError("IMPORT_NOT_FOUND")
        return created


def _normalize_extracted(item: ExtractedShift, timezone: str) -> NewImportItem:
    warnings = list(dict.fromkeys(item.warnings))
    raw_payload = item.model_dump(mode="json")
    if item.needs_review and "MODEL_MARKED_FOR_REVIEW" not in warnings:
        warnings.append("MODEL_MARKED_FOR_REVIEW")
    if item.work_date is None or item.start_time is None or item.end_time is None:
        warnings.append("MISSING_DATE_OR_TIME")
        return NewImportItem(
            raw_payload=raw_payload,
            work_date=item.work_date,
            start_at=None,
            end_at=None,
            break_minutes=item.break_minutes,
            shift_type=item.shift_type,
            notes=item.notes,
            validation_status="invalid",
            warnings=list(dict.fromkeys(warnings)),
        )
    try:
        zone = ZoneInfo(timezone)
    except ZoneInfoNotFoundError as error:
        raise ImportServiceError("PROFILE_TIMEZONE_INVALID") from error
    start_local = datetime.combine(item.work_date, item.start_time, zone)
    end_date = item.work_date + timedelta(days=1 if item.crosses_midnight else 0)
    end_local = datetime.combine(end_date, item.end_time, zone)
    if _is_ambiguous(start_local) or _is_ambiguous(end_local):
        warnings.append("AMBIGUOUS_LOCAL_TIME")
    if _is_nonexistent(start_local) or _is_nonexistent(end_local):
        warnings.append("NONEXISTENT_LOCAL_TIME")
    try:
        Shift(
            start_at=start_local.astimezone(UTC),
            end_at=end_local.astimezone(UTC),
            break_minutes=item.break_minutes,
            timezone=timezone,
            shift_type=item.shift_type,
        )
    except ScheduleValidationError as error:
        warnings.append(f"INVALID_SHIFT:{error}")
        status = "invalid"
    else:
        status = (
            "invalid"
            if "AMBIGUOUS_LOCAL_TIME" in warnings
            or "NONEXISTENT_LOCAL_TIME" in warnings
            else "valid"
        )
    return NewImportItem(
        raw_payload=raw_payload,
        work_date=item.work_date,
        start_at=start_local.astimezone(UTC),
        end_at=end_local.astimezone(UTC),
        break_minutes=item.break_minutes,
        shift_type=item.shift_type,
        notes=item.notes,
        validation_status=status,
        warnings=list(dict.fromkeys(warnings)),
    )


def _is_ambiguous(value: datetime) -> bool:
    return value.replace(fold=0).utcoffset() != value.replace(fold=1).utcoffset()


def _is_nonexistent(value: datetime) -> bool:
    round_trip = value.astimezone(UTC).astimezone(value.tzinfo)
    return round_trip.replace(tzinfo=None) != value.replace(tzinfo=None)

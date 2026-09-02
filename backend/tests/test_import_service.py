from datetime import UTC, datetime
from pathlib import Path
from typing import cast
from uuid import UUID

import pytest
from sqlalchemy import Connection

from backend.app.integrations.gemini import GeminiExtractionError
from backend.app.repositories.imports import (
    ImportItemRecord,
    ImportRecord,
    NewImport,
    NewImportItem,
)
from backend.app.schemas.imports import (
    ExtractedShift,
    ImportItemUpdateRequest,
    ScheduleExtraction,
)
from backend.app.services.imports import (
    ImportConflictError,
    ImportService,
    ValidatedUploadInfo,
)

CONNECTION = cast(Connection, object())
IMPORT_ID = UUID("00000000-0000-0000-0000-000000000401")
ITEM_ID = UUID("00000000-0000-0000-0000-000000000402")
SHIFT_ID = UUID("00000000-0000-0000-0000-000000000403")
NOW = datetime(2026, 9, 2, tzinfo=UTC)


class FakeExtractor:
    model_name = "synthetic-gemini"
    prompt_version = "schedule_extraction_v1"

    def __init__(self, fail: bool = False) -> None:
        self.fail = fail

    def extract(self, path: Path, media_type: str, timezone: str) -> ScheduleExtraction:
        if self.fail:
            raise GeminiExtractionError("GEMINI_QUOTA_EXHAUSTED")
        return ScheduleExtraction(
            items=[
                ExtractedShift(
                    work_date="2026-09-03",
                    start_time="22:00",
                    end_time="06:00",
                    crosses_midnight=True,
                    shift_type="night",
                    needs_review=True,
                    warnings=["LOW_CONTRAST"],
                ),
                ExtractedShift(
                    work_date="2026-09-04",
                    start_time=None,
                    end_time="17:00",
                    needs_review=True,
                ),
            ]
        )


class FakeImportRepository:
    def __init__(self) -> None:
        self.status = "uploaded"
        self.error_code: str | None = None
        self.items: list[ImportItemRecord] = []
        self.committed: list[UUID] = []

    def get_profile_timezone(self, connection: Connection) -> str | None:
        return "Asia/Taipei"

    def create_import(self, connection: Connection, new_import: NewImport) -> UUID:
        return IMPORT_ID

    def set_extracting(
        self, connection: Connection, import_id: UUID, model: str, prompt: str
    ) -> None:
        self.status = "extracting"

    def save_extraction(
        self, connection: Connection, import_id: UUID, items: list[NewImportItem]
    ) -> None:
        self.status = "review"
        self.items = [to_record(item, index) for index, item in enumerate(items)]

    def set_failed(self, connection: Connection, import_id: UUID, code: str) -> None:
        self.status = "failed"
        self.error_code = code

    def get_import(
        self, connection: Connection, import_id: UUID
    ) -> ImportRecord | None:
        return ImportRecord(
            id=IMPORT_ID,
            filename="generated.png",
            media_type="image/png",
            status=self.status,
            model_name="synthetic-gemini",
            prompt_version="schedule_extraction_v1",
            error_code=self.error_code,
            created_at=NOW,
            updated_at=NOW,
            items=self.items,
        )

    def update_item(
        self,
        connection: Connection,
        import_id: UUID,
        item_id: UUID,
        item: NewImportItem,
        confirmed: bool,
    ) -> bool:
        for index, current in enumerate(self.items):
            if current.id == item_id:
                self.items[index] = to_record(item, index, confirmed)
                return True
        return False

    def commit(self, connection: Connection, import_id: UUID) -> list[UUID] | None:
        if not self.committed:
            self.committed = [SHIFT_ID]
            self.items[0] = ImportItemRecord(
                **{
                    **record_values(self.items[0]),
                    "committed_shift_id": SHIFT_ID,
                }
            )
        self.status = "committed"
        return self.committed


def to_record(
    item: NewImportItem, index: int, confirmed: bool = False
) -> ImportItemRecord:
    return ImportItemRecord(
        id=UUID(f"00000000-0000-0000-0000-{402 + index:012d}"),
        work_date=item.work_date,
        start_at=item.start_at,
        end_at=item.end_at,
        break_minutes=item.break_minutes,
        shift_type=item.shift_type,
        notes=item.notes,
        validation_status=item.validation_status,
        needs_review=bool(item.raw_payload.get("needs_review")),
        warnings=item.warnings,
        confirmed=confirmed,
        committed_shift_id=None,
    )


def record_values(item: ImportItemRecord) -> dict[str, object]:
    return {
        field: getattr(item, field)
        for field in item.__dataclass_fields__
        if field != "committed_shift_id"
    }


def upload() -> ValidatedUploadInfo:
    return ValidatedUploadInfo(
        Path("synthetic.png"), "generated.png", "image/png", "a" * 64
    )


def test_extraction_normalizes_overnight_and_rejects_missing_time() -> None:
    repository = FakeImportRepository()
    result = ImportService(repository, FakeExtractor()).create_and_extract(
        CONNECTION, upload()
    )

    assert result.status == "review"
    assert result.items[0].validation_status == "valid"
    assert result.items[0].start_at == datetime(2026, 9, 3, 14, tzinfo=UTC)
    assert result.items[0].end_at == datetime(2026, 9, 3, 22, tzinfo=UTC)
    assert result.items[0].needs_review is True
    assert result.items[1].validation_status == "invalid"
    assert "MISSING_DATE_OR_TIME" in result.items[1].warnings


def test_gemini_failure_is_persisted_with_safe_retryable_code() -> None:
    repository = FakeImportRepository()
    result = ImportService(repository, FakeExtractor(fail=True)).create_and_extract(
        CONNECTION, upload()
    )

    assert result.status == "failed"
    assert result.error_code == "GEMINI_QUOTA_EXHAUSTED"
    assert result.items == []


def test_only_valid_confirmed_items_commit_and_repeat_is_idempotent() -> None:
    repository = FakeImportRepository()
    service = ImportService(repository, FakeExtractor())
    service.create_and_extract(CONNECTION, upload())

    with pytest.raises(ImportConflictError, match="NO_CONFIRMED_ITEMS"):
        service.commit(CONNECTION, IMPORT_ID)
    with pytest.raises(ImportConflictError, match="INVALID_ITEM"):
        service.update_item(
            CONNECTION,
            IMPORT_ID,
            UUID("00000000-0000-0000-0000-000000000403"),
            ImportItemUpdateRequest(confirmed=True),
        )

    service.update_item(
        CONNECTION, IMPORT_ID, ITEM_ID, ImportItemUpdateRequest(confirmed=True)
    )
    assert service.commit(CONNECTION, IMPORT_ID) == [SHIFT_ID]
    assert service.commit(CONNECTION, IMPORT_ID) == [SHIFT_ID]

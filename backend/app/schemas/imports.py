from datetime import date, datetime, time
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ExtractedShift(BaseModel):
    model_config = ConfigDict(extra="forbid")

    work_date: date | None
    start_time: time | None
    end_time: time | None
    crosses_midnight: bool = False
    break_minutes: int = Field(default=0, ge=0, le=1440)
    shift_type: str = Field(default="other", min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    needs_review: bool = False
    warnings: list[str] = Field(default_factory=list, max_length=20)


class ScheduleExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ExtractedShift] = Field(max_length=200)


class ImportItemUpdateRequest(BaseModel):
    work_date: date | None = None
    start_time: time | None = None
    end_time: time | None = None
    crosses_midnight: bool | None = None
    break_minutes: int | None = Field(default=None, ge=0, le=1440)
    shift_type: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)
    confirmed: bool | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "ImportItemUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        return self


class ImportItemResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_date: date | None
    start_at: datetime | None
    end_at: datetime | None
    break_minutes: int | None
    shift_type: str | None
    notes: str | None
    validation_status: Literal["pending", "valid", "invalid"]
    needs_review: bool
    warnings: list[str]
    confirmed: bool
    committed_shift_id: UUID | None


class ShiftImportResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    filename: str
    media_type: Literal["image/jpeg", "image/png", "application/pdf"]
    status: Literal[
        "uploaded", "extracting", "review", "committed", "failed", "expired"
    ]
    model_name: str | None
    prompt_version: str | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime
    items: list[ImportItemResponse]


class ImportCommitResponse(BaseModel):
    import_id: UUID
    status: Literal["committed"]
    created_shift_ids: list[UUID]

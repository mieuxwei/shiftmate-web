from datetime import date, datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ShiftCreateRequest(BaseModel):
    start_at: datetime
    end_at: datetime
    break_minutes: int = Field(default=0, ge=0, le=1440)
    shift_type: str = Field(min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)


class ShiftUpdateRequest(BaseModel):
    start_at: datetime | None = None
    end_at: datetime | None = None
    break_minutes: int | None = Field(default=None, ge=0, le=1440)
    shift_type: str | None = Field(default=None, min_length=1, max_length=50)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def validate_patch(self) -> "ShiftUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field_name in ("start_at", "end_at", "break_minutes", "shift_type"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class ShiftResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    work_date: date
    start_at: datetime
    end_at: datetime
    break_minutes: int
    shift_type: str
    notes: str | None
    source: Literal["manual", "import", "calendar"]
    created_at: datetime
    updated_at: datetime

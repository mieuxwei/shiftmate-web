from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, model_validator


class PayRateCreateRequest(BaseModel):
    hourly_rate: Decimal = Field(gt=0, max_digits=12, decimal_places=2)
    effective_from: date
    effective_to: date | None = None


class PayRateUpdateRequest(BaseModel):
    hourly_rate: Decimal | None = Field(
        default=None, gt=0, max_digits=12, decimal_places=2
    )
    effective_from: date | None = None
    effective_to: date | None = None

    @model_validator(mode="after")
    def validate_patch(self) -> "PayRateUpdateRequest":
        if not self.model_fields_set:
            raise ValueError("At least one field must be provided")
        for field_name in ("hourly_rate", "effective_from"):
            if (
                field_name in self.model_fields_set
                and getattr(self, field_name) is None
            ):
                raise ValueError(f"{field_name} cannot be null")
        return self


class PayRateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    hourly_rate: Decimal
    effective_from: date
    effective_to: date | None
    created_at: datetime
    updated_at: datetime

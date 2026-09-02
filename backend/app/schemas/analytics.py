from datetime import date
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class AnalyticsSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date_from: date
    date_to: date
    timezone: str
    currency: str
    shift_count: int
    total_paid_hours: Decimal
    estimated_pay: Decimal
    shift_type_counts: dict[str, int]
    weekly_hours: dict[date, Decimal]
    longest_consecutive_days: int

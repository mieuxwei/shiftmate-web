from datetime import date
from decimal import Decimal

from pydantic import BaseModel

from backend.app.schemas.assistant import AssistantQueryResponse
from backend.app.schemas.policies import PolicyCitation
from backend.app.schemas.shifts import ShiftResponse


class ShiftListResult(BaseModel):
    shifts: list[ShiftResponse]


class WorkHoursResult(BaseModel):
    date_from: date
    date_to: date
    timezone: str
    shift_count: int
    total_paid_hours: Decimal
    weekly_hours: dict[date, Decimal]
    longest_consecutive_days: int


class PayrollSummaryResult(BaseModel):
    date_from: date
    date_to: date
    currency: str
    shift_count: int
    total_paid_hours: Decimal
    estimated_pay: Decimal
    disclaimer: str


class PolicySearchResult(BaseModel):
    question: str
    refused: bool
    citations: list[PolicyCitation]


class ComplianceAnalysisResult(BaseModel):
    result: AssistantQueryResponse


class CalendarExportResult(BaseModel):
    filename: str
    media_type: str
    content: str

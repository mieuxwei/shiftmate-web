from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from backend.app.schemas.policies import PolicyCitation

AssistantIntent = Literal["schedule", "policy", "hybrid", "unsupported"]


class AssistantQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)
    date_from: date
    date_to: date


class AssistantScheduleFacts(BaseModel):
    date_from: date
    date_to: date
    timezone: str
    currency: str
    shift_count: int
    total_paid_hours: Decimal
    estimated_pay: Decimal
    longest_consecutive_days: int


class AssistantToolTrace(BaseModel):
    name: Literal["schedule_summary", "policy_retrieval", "rule_evaluator"]
    status: Literal["used", "insufficient"]


class AssistantQueryResponse(BaseModel):
    answer: str
    intent: AssistantIntent
    refused: bool
    citations: list[PolicyCitation]
    schedule_facts: AssistantScheduleFacts | None
    tools: list[AssistantToolTrace]
    prompt_version: str | None
    model_name: str | None

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class PolicyDocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    title: str
    filename: str
    status: Literal["uploaded", "indexing", "ready", "failed"]
    page_count: int | None
    error_code: str | None = None
    created_at: datetime
    updated_at: datetime


class PolicyUploadResponse(BaseModel):
    document: PolicyDocumentResponse
    duplicate: bool


class PolicyQueryRequest(BaseModel):
    question: str = Field(min_length=2, max_length=1000)


class PolicyCitation(BaseModel):
    document_id: UUID
    chunk_id: UUID
    title: str
    page_number: int
    excerpt: str = Field(max_length=320)


class PolicyAnswerResponse(BaseModel):
    answer: str
    refused: bool
    citations: list[PolicyCitation]
    prompt_version: str
    model_name: str | None

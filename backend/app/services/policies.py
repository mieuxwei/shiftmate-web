from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol
from uuid import UUID

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from sqlalchemy import Connection

from backend.app.integrations.gemini_rag import RAG_PROMPT_VERSION
from backend.app.repositories.policies import (
    NewPolicyChunk,
    NewPolicyDocument,
    PolicyDocumentRecord,
    PolicyRepository,
)
from backend.app.schemas.policies import PolicyAnswerResponse, PolicyCitation
from backend.app.services.policy_text import chunk_policy_pages, extract_policy_pages
from backend.app.services.retrieval import OwnerScopedPolicyRetriever

EMBEDDING_DIMENSIONS = 768


class PolicyServiceError(ValueError):
    pass


class PolicyNotFoundError(PolicyServiceError):
    pass


class GroundedAnswerer(Protocol):
    model_name: str
    prompt_version: str

    def answer(self, question: str, evidence: list[dict[str, object]]) -> str: ...


@dataclass(frozen=True, slots=True)
class PolicyUploadInfo:
    path: Path
    title: str
    filename: str
    sha256: str
    page_count: int


@dataclass(frozen=True, slots=True)
class PolicyEvidence:
    text: str
    citation: PolicyCitation


class PolicyService:
    def __init__(self, repository: PolicyRepository) -> None:
        self.repository = repository

    def create_draft(
        self, connection: Connection, upload: PolicyUploadInfo
    ) -> tuple[PolicyDocumentRecord, bool]:
        return self.repository.create_or_get_document(
            connection,
            NewPolicyDocument(
                title=upload.title.strip(),
                filename=upload.filename,
                sha256=upload.sha256,
                page_count=upload.page_count,
            ),
        )

    def prepare_chunks(
        self, upload: PolicyUploadInfo, embeddings: Embeddings
    ) -> list[NewPolicyChunk]:
        text_chunks = chunk_policy_pages(extract_policy_pages(upload.path))
        vectors = embeddings.embed_documents([chunk.content for chunk in text_chunks])
        if len(vectors) != len(text_chunks) or any(
            len(vector) != EMBEDDING_DIMENSIONS for vector in vectors
        ):
            raise PolicyServiceError("GEMINI_INVALID_RESPONSE")
        return [
            NewPolicyChunk(
                content=chunk.content,
                page_number=chunk.page_number,
                chunk_index=chunk.chunk_index,
                metadata={
                    "title": upload.title,
                    "filename": upload.filename,
                    "sha256": upload.sha256,
                    "page_number": chunk.page_number,
                },
                embedding=vector,
            )
            for chunk, vector in zip(text_chunks, vectors, strict=True)
        ]

    def complete_indexing(
        self,
        connection: Connection,
        document_id: UUID,
        chunks: Sequence[NewPolicyChunk],
    ) -> PolicyDocumentRecord:
        self.repository.mark_ready(connection, document_id, chunks)
        return self.get_document(connection, document_id)

    def fail_indexing(
        self, connection: Connection, document_id: UUID, error_code: str
    ) -> PolicyDocumentRecord:
        self.repository.mark_failed(connection, document_id, error_code)
        return self.get_document(connection, document_id)

    def get_document(
        self, connection: Connection, document_id: UUID
    ) -> PolicyDocumentRecord:
        record = self.repository.get_document(connection, document_id)
        if record is None:
            raise PolicyNotFoundError("POLICY_NOT_FOUND")
        return record

    def list_documents(self, connection: Connection) -> list[PolicyDocumentRecord]:
        return self.repository.list_documents(connection)

    def delete_document(self, connection: Connection, document_id: UUID) -> None:
        if not self.repository.delete_document(connection, document_id):
            raise PolicyNotFoundError("POLICY_NOT_FOUND")

    def answer_question(
        self,
        connection: Connection,
        question: str,
        embeddings: Embeddings,
        answerer: GroundedAnswerer,
        top_k: int,
        score_threshold: float,
    ) -> PolicyAnswerResponse:
        evidence_items = self.retrieve_evidence(
            connection, question, embeddings, top_k, score_threshold
        )
        if not evidence_items:
            return PolicyAnswerResponse(
                answer="上傳的規章中沒有足夠資料可以回答這個問題。",
                refused=True,
                citations=[],
                prompt_version=RAG_PROMPT_VERSION,
                model_name=None,
            )
        evidence = [
            {
                "label": f"source_{index + 1}",
                "title": item.citation.title,
                "page_number": item.citation.page_number,
                "text": item.text,
            }
            for index, item in enumerate(evidence_items)
        ]
        answer = answerer.answer(question.strip(), evidence)
        return PolicyAnswerResponse(
            answer=answer,
            refused=False,
            citations=[item.citation for item in evidence_items],
            prompt_version=answerer.prompt_version,
            model_name=answerer.model_name,
        )

    def retrieve_evidence(
        self,
        connection: Connection,
        question: str,
        embeddings: Embeddings,
        top_k: int,
        score_threshold: float,
    ) -> list[PolicyEvidence]:
        retriever = OwnerScopedPolicyRetriever(
            connection=connection,
            embeddings=embeddings,
            top_k=top_k,
            score_threshold=score_threshold,
        )
        documents = retriever.retrieve_without_external_tracing(question.strip())
        return [
            PolicyEvidence(text=document.page_content, citation=_citation(document))
            for document in documents
        ]


def _evidence(index: int, document: Document) -> dict[str, object]:
    return {
        "label": f"source_{index + 1}",
        "title": str(document.metadata["title"]),
        "page_number": int(document.metadata["page_number"]),
        "text": document.page_content,
    }


def _citation(document: Document) -> PolicyCitation:
    excerpt = " ".join(document.page_content.split())[:320]
    return PolicyCitation(
        document_id=UUID(str(document.metadata["document_id"])),
        chunk_id=UUID(str(document.metadata["chunk_id"])),
        title=str(document.metadata["title"]),
        page_number=int(document.metadata["page_number"]),
        excerpt=excerpt,
    )

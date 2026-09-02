import json
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from typing import Protocol, cast
from uuid import UUID

from sqlalchemy import Connection, RowMapping, text


@dataclass(frozen=True, slots=True)
class NewPolicyDocument:
    title: str
    filename: str
    sha256: str
    page_count: int


@dataclass(frozen=True, slots=True)
class NewPolicyChunk:
    content: str
    page_number: int
    chunk_index: int
    metadata: dict[str, object]
    embedding: Sequence[float]


@dataclass(frozen=True, slots=True)
class PolicyDocumentRecord:
    id: UUID
    title: str
    filename: str
    status: str
    page_count: int | None
    error_code: str | None
    created_at: datetime
    updated_at: datetime


class PolicyRepository(Protocol):
    def create_or_get_document(
        self, connection: Connection, document: NewPolicyDocument
    ) -> tuple[PolicyDocumentRecord, bool]: ...
    def mark_ready(
        self,
        connection: Connection,
        document_id: UUID,
        chunks: Sequence[NewPolicyChunk],
    ) -> None: ...
    def mark_failed(
        self, connection: Connection, document_id: UUID, error_code: str
    ) -> None: ...
    def get_document(
        self, connection: Connection, document_id: UUID
    ) -> PolicyDocumentRecord | None: ...
    def list_documents(self, connection: Connection) -> list[PolicyDocumentRecord]: ...
    def delete_document(self, connection: Connection, document_id: UUID) -> bool: ...


class PostgresPolicyRepository:
    def create_or_get_document(
        self, connection: Connection, document: NewPolicyDocument
    ) -> tuple[PolicyDocumentRecord, bool]:
        inserted = (
            connection.execute(
                text(
                    """
                INSERT INTO policy_documents (
                    owner_id, title, filename, sha256, status, page_count
                ) VALUES (
                    app_private.current_user_id(), :title, :filename, :sha256,
                    'indexing', :page_count
                )
                ON CONFLICT (owner_id, sha256) DO NOTHING
                RETURNING id, title, filename, status, page_count, error_code,
                          created_at, updated_at
                """
                ),
                {
                    "title": document.title,
                    "filename": document.filename,
                    "sha256": document.sha256,
                    "page_count": document.page_count,
                },
            )
            .mappings()
            .one_or_none()
        )
        if inserted is not None:
            return _to_document(inserted), False
        existing = (
            connection.execute(
                text(
                    """
                SELECT id, title, filename, status, page_count, error_code,
                       created_at, updated_at
                FROM policy_documents WHERE sha256 = :sha256
                """
                ),
                {"sha256": document.sha256},
            )
            .mappings()
            .one()
        )
        return _to_document(existing), True

    def mark_ready(
        self,
        connection: Connection,
        document_id: UUID,
        chunks: Sequence[NewPolicyChunk],
    ) -> None:
        connection.execute(
            text("DELETE FROM policy_chunks WHERE document_id = :document_id"),
            {"document_id": document_id},
        )
        for chunk in chunks:
            connection.execute(
                text(
                    """
                    INSERT INTO policy_chunks (
                        document_id, owner_id, content, page_number, chunk_index,
                        metadata, embedding
                    ) VALUES (
                        :document_id, app_private.current_user_id(), :content,
                        :page_number, :chunk_index, CAST(:metadata AS jsonb),
                        CAST(:embedding AS vector)
                    )
                    """
                ),
                {
                    "document_id": document_id,
                    "content": chunk.content,
                    "page_number": chunk.page_number,
                    "chunk_index": chunk.chunk_index,
                    "metadata": json.dumps(chunk.metadata),
                    "embedding": _vector_literal(chunk.embedding),
                },
            )
        connection.execute(
            text(
                """
                UPDATE policy_documents
                SET status = 'ready', error_code = NULL, updated_at = now()
                WHERE id = :document_id AND status = 'indexing'
                """
            ),
            {"document_id": document_id},
        )

    def mark_failed(
        self, connection: Connection, document_id: UUID, error_code: str
    ) -> None:
        connection.execute(
            text(
                """
                UPDATE policy_documents
                SET status = 'failed', error_code = :error_code, updated_at = now()
                WHERE id = :document_id AND status = 'indexing'
                """
            ),
            {"document_id": document_id, "error_code": error_code},
        )

    def get_document(
        self, connection: Connection, document_id: UUID
    ) -> PolicyDocumentRecord | None:
        row = (
            connection.execute(
                text(
                    """
                SELECT id, title, filename, status, page_count, error_code,
                       created_at, updated_at
                FROM policy_documents WHERE id = :document_id
                """
                ),
                {"document_id": document_id},
            )
            .mappings()
            .one_or_none()
        )
        return _to_document(row) if row is not None else None

    def list_documents(self, connection: Connection) -> list[PolicyDocumentRecord]:
        rows = connection.execute(
            text(
                """
                SELECT id, title, filename, status, page_count, error_code,
                       created_at, updated_at
                FROM policy_documents ORDER BY created_at DESC, id DESC
                """
            )
        ).mappings()
        return [_to_document(row) for row in rows]

    def delete_document(self, connection: Connection, document_id: UUID) -> bool:
        deleted = connection.execute(
            text("DELETE FROM policy_documents WHERE id = :document_id RETURNING id"),
            {"document_id": document_id},
        ).scalar_one_or_none()
        return deleted is not None


def _vector_literal(values: Sequence[float]) -> str:
    return "[" + ",".join(format(value, ".9g") for value in values) + "]"


def _to_document(row: RowMapping) -> PolicyDocumentRecord:
    return PolicyDocumentRecord(
        id=cast(UUID, row["id"]),
        title=cast(str, row["title"]),
        filename=cast(str, row["filename"]),
        status=cast(str, row["status"]),
        page_count=cast(int | None, row["page_count"]),
        error_code=cast(str | None, row["error_code"]),
        created_at=cast(datetime, row["created_at"]),
        updated_at=cast(datetime, row["updated_at"]),
    )

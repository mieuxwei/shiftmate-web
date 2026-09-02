from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from pydantic import ConfigDict, Field
from sqlalchemy import Connection, text

from backend.app.repositories.policies import _vector_literal


class OwnerScopedPolicyRetriever(BaseRetriever):
    """LangChain retriever backed by application-owned pgvector tables and RLS."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    connection: Any
    embeddings: Embeddings
    top_k: int = Field(default=5, ge=1, le=10)
    score_threshold: float = Field(default=0.55, ge=-1, le=1)

    def retrieve_without_external_tracing(self, query: str) -> list[Document]:
        """Run retrieval with a no-op callback regardless of global tracing env."""
        return self._get_relevant_documents(
            query,
            run_manager=CallbackManagerForRetrieverRun.get_noop_manager(),
        )

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: CallbackManagerForRetrieverRun,
    ) -> list[Document]:
        del run_manager
        connection = self.connection
        if not isinstance(connection, Connection):
            raise TypeError("A SQLAlchemy Connection is required")
        query_embedding = self.embeddings.embed_query(query)
        rows = connection.execute(
            text(
                """
                SELECT ranked.chunk_id, ranked.document_id, ranked.content,
                       ranked.page_number, ranked.title, ranked.filename,
                       ranked.score
                FROM (
                    SELECT chunk.id AS chunk_id,
                           chunk.document_id,
                           chunk.content,
                           chunk.page_number,
                           document.title,
                           document.filename,
                           1 - (chunk.embedding <=> CAST(:embedding AS vector(768)))
                               AS score
                    FROM policy_chunks AS chunk
                    JOIN policy_documents AS document
                      ON document.id = chunk.document_id
                     AND document.owner_id = chunk.owner_id
                    WHERE chunk.owner_id = app_private.current_user_id()
                      AND document.status = 'ready'
                      AND chunk.embedding IS NOT NULL
                ) AS ranked
                WHERE ranked.score >= :score_threshold
                ORDER BY ranked.score DESC, ranked.chunk_id
                LIMIT :top_k
                """
            ),
            {
                "embedding": _vector_literal(query_embedding),
                "score_threshold": self.score_threshold,
                "top_k": self.top_k,
            },
        ).mappings()
        return [
            Document(
                page_content=row["content"],
                metadata={
                    "chunk_id": str(row["chunk_id"]),
                    "document_id": str(row["document_id"]),
                    "page_number": row["page_number"],
                    "title": row["title"],
                    "filename": row["filename"],
                    "score": float(row["score"]),
                },
            )
            for row in rows
        ]

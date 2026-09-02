"""Add policy RAG dimensions, deduplication, and vector index.

Revision ID: 20260902_0004
Revises: 20260902_0003
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "20260902_0004"
down_revision: str | None = "20260902_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "policy_documents",
        sa.Column("error_code", sa.Text(), nullable=True),
    )
    op.create_unique_constraint(
        "uq_policy_documents_owner_sha256",
        "policy_documents",
        ["owner_id", "sha256"],
    )
    op.execute(
        "ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector(768) "
        "USING embedding::vector(768)"
    )
    op.execute(
        "CREATE INDEX ix_policy_chunks_embedding_cosine "
        "ON policy_chunks USING hnsw (embedding vector_cosine_ops) "
        "WHERE embedding IS NOT NULL"
    )


def downgrade() -> None:
    op.execute("DROP INDEX ix_policy_chunks_embedding_cosine")
    op.execute(
        "ALTER TABLE policy_chunks ALTER COLUMN embedding TYPE vector "
        "USING embedding::vector"
    )
    op.drop_constraint(
        "uq_policy_documents_owner_sha256",
        "policy_documents",
        type_="unique",
    )
    op.drop_column("policy_documents", "error_code")

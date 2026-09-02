"""Add the remaining M2 schema and pgvector.

Revision ID: 20260902_0002
Revises: 20260902_0001
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0002"
down_revision: str | None = "20260902_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


class Vector(sa.types.UserDefinedType):
    cache_ok = True

    def get_col_spec(self, **kw: object) -> str:
        return "vector"


def uuid_primary_key() -> sa.Column[object]:
    return sa.Column(
        "id",
        postgresql.UUID(as_uuid=True),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
    )


def owner_column() -> sa.Column[object]:
    return sa.Column(
        "owner_id",
        postgresql.UUID(as_uuid=True),
        sa.ForeignKey("profiles.id", ondelete="CASCADE"),
        nullable=False,
    )


def created_at_column() -> sa.Column[object]:
    return sa.Column(
        "created_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def updated_at_column() -> sa.Column[object]:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        nullable=False,
        server_default=sa.text("now()"),
    )


def apply_owner_policy(table_name: str) -> None:
    op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
    op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
    op.execute(
        f"""
        CREATE POLICY {table_name}_owner_isolation ON {table_name}
        FOR ALL
        USING (owner_id = app_private.current_user_id())
        WITH CHECK (owner_id = app_private.current_user_id())
        """
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "pay_rates",
        uuid_primary_key(),
        owner_column(),
        sa.Column("hourly_rate", sa.Numeric(12, 2), nullable=False),
        sa.Column("effective_from", sa.Date(), nullable=False),
        sa.Column("effective_to", sa.Date(), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.CheckConstraint("hourly_rate > 0", name="ck_pay_rates_positive"),
        sa.CheckConstraint(
            "effective_to IS NULL OR effective_to >= effective_from",
            name="ck_pay_rates_effective_range",
        ),
    )
    op.create_index(
        "ix_pay_rates_owner_effective_from",
        "pay_rates",
        ["owner_id", "effective_from"],
    )

    op.create_table(
        "shift_imports",
        uuid_primary_key(),
        owner_column(),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("media_type", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="uploaded"),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("prompt_version", sa.Text(), nullable=True),
        sa.Column("error_code", sa.Text(), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.CheckConstraint("sha256 ~ '^[0-9a-f]{64}$'", name="ck_shift_imports_sha256"),
        sa.CheckConstraint(
            "status IN ('uploaded', 'extracting', 'review', 'committed', "
            "'failed', 'expired')",
            name="ck_shift_imports_status",
        ),
        sa.UniqueConstraint("id", "owner_id", name="uq_shift_imports_id_owner"),
    )
    op.create_index(
        "ix_shift_imports_owner_created_at",
        "shift_imports",
        ["owner_id", "created_at"],
    )

    op.create_table(
        "shift_import_items",
        uuid_primary_key(),
        sa.Column("import_id", postgresql.UUID(as_uuid=True), nullable=False),
        owner_column(),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("normalized_work_date", sa.Date(), nullable=True),
        sa.Column("normalized_start_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_end_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("normalized_break_minutes", sa.SmallInteger(), nullable=True),
        sa.Column("normalized_shift_type", sa.Text(), nullable=True),
        sa.Column("normalized_notes", sa.Text(), nullable=True),
        sa.Column(
            "validation_status", sa.Text(), nullable=False, server_default="pending"
        ),
        sa.Column(
            "warnings",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("confirmed_at", sa.DateTime(timezone=True), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.ForeignKeyConstraint(
            ["import_id", "owner_id"],
            ["shift_imports.id", "shift_imports.owner_id"],
            name="fk_shift_import_items_import_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(raw_payload) = 'object'",
            name="ck_shift_import_items_raw_payload_object",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(warnings) = 'array'",
            name="ck_shift_import_items_warnings_array",
        ),
        sa.CheckConstraint(
            "validation_status IN ('pending', 'valid', 'invalid')",
            name="ck_shift_import_items_validation_status",
        ),
        sa.CheckConstraint(
            "normalized_break_minutes IS NULL OR "
            "normalized_break_minutes BETWEEN 0 AND 1440",
            name="ck_shift_import_items_break_minutes",
        ),
        sa.CheckConstraint(
            "normalized_start_at IS NULL OR normalized_end_at IS NULL OR "
            "normalized_end_at > normalized_start_at",
            name="ck_shift_import_items_time_range",
        ),
    )
    op.create_index("ix_shift_import_items_import", "shift_import_items", ["import_id"])
    op.create_index("ix_shift_import_items_owner", "shift_import_items", ["owner_id"])

    op.create_table(
        "policy_documents",
        uuid_primary_key(),
        owner_column(),
        sa.Column("title", sa.Text(), nullable=False),
        sa.Column("filename", sa.Text(), nullable=False),
        sa.Column("sha256", sa.String(64), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="uploaded"),
        sa.Column("page_count", sa.Integer(), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.CheckConstraint(
            "sha256 ~ '^[0-9a-f]{64}$'", name="ck_policy_documents_sha256"
        ),
        sa.CheckConstraint(
            "status IN ('uploaded', 'indexing', 'ready', 'failed')",
            name="ck_policy_documents_status",
        ),
        sa.CheckConstraint(
            "page_count IS NULL OR page_count > 0",
            name="ck_policy_documents_page_count",
        ),
        sa.UniqueConstraint("id", "owner_id", name="uq_policy_documents_id_owner"),
    )
    op.create_index(
        "ix_policy_documents_owner_created_at",
        "policy_documents",
        ["owner_id", "created_at"],
    )

    op.create_table(
        "policy_chunks",
        uuid_primary_key(),
        sa.Column("document_id", postgresql.UUID(as_uuid=True), nullable=False),
        owner_column(),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("page_number", sa.Integer(), nullable=False),
        sa.Column("chunk_index", sa.Integer(), nullable=False),
        sa.Column(
            "metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("embedding", Vector(), nullable=True),
        created_at_column(),
        sa.ForeignKeyConstraint(
            ["document_id", "owner_id"],
            ["policy_documents.id", "policy_documents.owner_id"],
            name="fk_policy_chunks_document_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint("page_number > 0", name="ck_policy_chunks_page_number"),
        sa.CheckConstraint("chunk_index >= 0", name="ck_policy_chunks_chunk_index"),
        sa.CheckConstraint(
            "jsonb_typeof(metadata) = 'object'",
            name="ck_policy_chunks_metadata_object",
        ),
        sa.UniqueConstraint(
            "document_id", "chunk_index", name="uq_policy_chunks_document_index"
        ),
    )
    op.create_index(
        "ix_policy_chunks_owner_document",
        "policy_chunks",
        ["owner_id", "document_id"],
    )

    op.create_table(
        "calendar_connections",
        uuid_primary_key(),
        owner_column(),
        sa.Column("encrypted_refresh_token", sa.Text(), nullable=False),
        sa.Column(
            "scopes",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="active"),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.CheckConstraint(
            "jsonb_typeof(scopes) = 'array'",
            name="ck_calendar_connections_scopes_array",
        ),
        sa.CheckConstraint(
            "status IN ('active', 'revoked', 'error')",
            name="ck_calendar_connections_status",
        ),
    )
    op.create_index(
        "ix_calendar_connections_owner", "calendar_connections", ["owner_id"]
    )

    op.create_table(
        "calendar_sync_records",
        uuid_primary_key(),
        sa.Column("shift_id", postgresql.UUID(as_uuid=True), nullable=False),
        owner_column(),
        sa.Column("external_event_id", sa.Text(), nullable=True),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        created_at_column(),
        updated_at_column(),
        sa.ForeignKeyConstraint(
            ["shift_id", "owner_id"],
            ["shifts.id", "shifts.owner_id"],
            name="fk_calendar_sync_records_shift_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'synced', 'failed', 'deleted')",
            name="ck_calendar_sync_records_status",
        ),
        sa.CheckConstraint(
            "retry_count >= 0", name="ck_calendar_sync_records_retry_count"
        ),
        sa.UniqueConstraint(
            "owner_id",
            "external_event_id",
            name="uq_calendar_sync_records_owner_event",
        ),
    )
    op.create_index(
        "ix_calendar_sync_records_owner_shift",
        "calendar_sync_records",
        ["owner_id", "shift_id"],
    )

    op.create_table(
        "chat_sessions",
        uuid_primary_key(),
        owner_column(),
        sa.Column("title", sa.Text(), nullable=True),
        created_at_column(),
        updated_at_column(),
        sa.UniqueConstraint("id", "owner_id", name="uq_chat_sessions_id_owner"),
    )
    op.create_index(
        "ix_chat_sessions_owner_updated_at",
        "chat_sessions",
        ["owner_id", "updated_at"],
    )

    op.create_table(
        "chat_messages",
        uuid_primary_key(),
        sa.Column("session_id", postgresql.UUID(as_uuid=True), nullable=False),
        owner_column(),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("selected_route", sa.Text(), nullable=True),
        sa.Column(
            "cited_chunk_ids",
            postgresql.ARRAY(postgresql.UUID(as_uuid=True)),
            nullable=False,
            server_default=sa.text("'{}'::uuid[]"),
        ),
        sa.Column(
            "tool_calls",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column(
            "usage_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        created_at_column(),
        sa.ForeignKeyConstraint(
            ["session_id", "owner_id"],
            ["chat_sessions.id", "chat_sessions.owner_id"],
            name="fk_chat_messages_session_owner",
            ondelete="CASCADE",
        ),
        sa.CheckConstraint(
            "role IN ('user', 'assistant', 'system', 'tool')",
            name="ck_chat_messages_role",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(tool_calls) = 'array'",
            name="ck_chat_messages_tool_calls_array",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(usage_metadata) = 'object'",
            name="ck_chat_messages_usage_metadata_object",
        ),
        sa.CheckConstraint(
            "latency_ms IS NULL OR latency_ms >= 0",
            name="ck_chat_messages_latency_ms",
        ),
    )
    op.create_index(
        "ix_chat_messages_owner_session_created_at",
        "chat_messages",
        ["owner_id", "session_id", "created_at"],
    )

    op.create_table(
        "tool_audit_logs",
        uuid_primary_key(),
        owner_column(),
        sa.Column("actor", sa.Text(), nullable=False),
        sa.Column("tool_name", sa.Text(), nullable=False),
        sa.Column(
            "sanitized_arguments",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("result_status", sa.Text(), nullable=False),
        sa.Column("confirmation_status", sa.Text(), nullable=False),
        created_at_column(),
        sa.CheckConstraint(
            "jsonb_typeof(sanitized_arguments) = 'object'",
            name="ck_tool_audit_logs_arguments_object",
        ),
        sa.CheckConstraint(
            "result_status IN ('success', 'error', 'denied')",
            name="ck_tool_audit_logs_result_status",
        ),
        sa.CheckConstraint(
            "confirmation_status IN "
            "('not_required', 'pending', 'confirmed', 'rejected')",
            name="ck_tool_audit_logs_confirmation_status",
        ),
    )
    op.create_index(
        "ix_tool_audit_logs_owner_created_at",
        "tool_audit_logs",
        ["owner_id", "created_at"],
    )

    op.create_table(
        "scheduled_job_runs",
        uuid_primary_key(),
        sa.Column("job_name", sa.Text(), nullable=False),
        sa.Column("logical_run_date", sa.Date(), nullable=False),
        sa.Column("status", sa.Text(), nullable=False, server_default="pending"),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error_code", sa.Text(), nullable=True),
        created_at_column(),
        sa.CheckConstraint(
            "status IN ('pending', 'running', 'succeeded', 'failed', 'skipped')",
            name="ck_scheduled_job_runs_status",
        ),
        sa.CheckConstraint(
            "finished_at IS NULL OR started_at IS NULL OR finished_at >= started_at",
            name="ck_scheduled_job_runs_time_range",
        ),
        sa.UniqueConstraint(
            "job_name",
            "logical_run_date",
            name="uq_scheduled_job_runs_job_date",
        ),
        sa.UniqueConstraint(
            "idempotency_key", name="uq_scheduled_job_runs_idempotency_key"
        ),
    )
    op.execute("ALTER TABLE scheduled_job_runs ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE scheduled_job_runs FORCE ROW LEVEL SECURITY")

    owner_tables = (
        "pay_rates",
        "shift_imports",
        "shift_import_items",
        "policy_documents",
        "policy_chunks",
        "calendar_connections",
        "calendar_sync_records",
        "chat_sessions",
        "chat_messages",
        "tool_audit_logs",
    )
    for table_name in owner_tables:
        apply_owner_policy(table_name)

    table_list = ", ".join(owner_tables)
    op.execute(
        f"""
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                GRANT USAGE ON SCHEMA public, app_private TO authenticated;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON {table_list} TO authenticated;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.drop_table("scheduled_job_runs")
    op.drop_table("tool_audit_logs")
    op.drop_table("chat_messages")
    op.drop_table("chat_sessions")
    op.drop_table("calendar_sync_records")
    op.drop_table("calendar_connections")
    op.drop_table("policy_chunks")
    op.drop_table("policy_documents")
    op.drop_table("shift_import_items")
    op.drop_table("shift_imports")
    op.drop_table("pay_rates")

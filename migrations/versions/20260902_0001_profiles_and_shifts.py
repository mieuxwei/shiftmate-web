"""Create the owner-isolated profiles and shifts foundation.

Revision ID: 20260902_0001
Revises:
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    # Supabase exposes the public schema through its Data API by default. Keep
    # Alembic's metadata table unreadable to API roles while allowing the
    # database owner used for migrations to maintain it.
    op.execute("ALTER TABLE alembic_version ENABLE ROW LEVEL SECURITY")
    op.execute("CREATE SCHEMA IF NOT EXISTS app_private")
    op.execute(
        """
        CREATE FUNCTION app_private.current_user_id()
        RETURNS uuid
        LANGUAGE sql
        STABLE
        PARALLEL SAFE
        AS $$
            SELECT COALESCE(
                NULLIF(current_setting('request.jwt.claim.sub', true), ''),
                NULLIF(
                    NULLIF(
                        current_setting('request.jwt.claims', true), ''
                    )::jsonb ->> 'sub',
                    ''
                )
            )::uuid
        $$
        """
    )

    op.create_table(
        "profiles",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("timezone", sa.Text(), nullable=False, server_default="Asia/Taipei"),
        sa.Column(
            "currency", sa.String(length=3), nullable=False, server_default="TWD"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint(
            "currency = upper(currency)", name="ck_profiles_currency_upper"
        ),
    )

    op.create_table(
        "shifts",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("work_date", sa.Date(), nullable=False),
        sa.Column("start_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("end_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "break_minutes", sa.SmallInteger(), nullable=False, server_default="0"
        ),
        sa.Column("shift_type", sa.Text(), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("source", sa.Text(), nullable=False, server_default="manual"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("end_at > start_at", name="ck_shifts_end_after_start"),
        sa.CheckConstraint(
            "break_minutes BETWEEN 0 AND 1440", name="ck_shifts_break_minutes"
        ),
        sa.CheckConstraint(
            "source IN ('manual', 'import', 'calendar')", name="ck_shifts_source"
        ),
        sa.UniqueConstraint("id", "owner_id", name="uq_shifts_id_owner"),
    )
    op.create_index("ix_shifts_owner_work_date", "shifts", ["owner_id", "work_date"])

    for table_name, identity_column in (("profiles", "id"), ("shifts", "owner_id")):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY {table_name}_owner_isolation ON {table_name}
            FOR ALL
            USING ({identity_column} = app_private.current_user_id())
            WITH CHECK ({identity_column} = app_private.current_user_id())
            """
        )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                GRANT USAGE ON SCHEMA public, app_private TO authenticated;
                GRANT SELECT, INSERT, UPDATE, DELETE
                ON profiles, shifts TO authenticated;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    op.drop_table("shifts")
    op.drop_table("profiles")
    op.execute("DROP FUNCTION app_private.current_user_id()")
    op.execute("DROP SCHEMA app_private")

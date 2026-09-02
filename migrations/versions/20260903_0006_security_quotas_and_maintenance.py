"""Add durable quotas and least-privilege maintenance access.

Revision ID: 20260903_0006
Revises: 20260902_0005
Create Date: 2026-09-03
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260903_0006"
down_revision: str | None = "20260902_0005"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "owner_daily_quotas",
        sa.Column(
            "owner_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("profiles.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("quota_name", sa.Text(), primary_key=True),
        sa.Column("used_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("used_units >= 0", name="ck_owner_daily_quotas_units"),
        sa.CheckConstraint(
            "quota_name IN ('upload')", name="ck_owner_daily_quotas_name"
        ),
    )
    op.create_table(
        "app_daily_quotas",
        sa.Column("usage_date", sa.Date(), primary_key=True),
        sa.Column("quota_name", sa.Text(), primary_key=True),
        sa.Column("used_units", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.CheckConstraint("used_units >= 0", name="ck_app_daily_quotas_units"),
        sa.CheckConstraint(
            "quota_name IN ('gemini_request')", name="ck_app_daily_quotas_name"
        ),
    )
    for table_name in ("owner_daily_quotas", "app_daily_quotas"):
        op.execute(f"ALTER TABLE {table_name} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {table_name} FORCE ROW LEVEL SECURITY")

    op.execute(
        """
        CREATE POLICY owner_daily_quotas_owner_isolation ON owner_daily_quotas
        FOR ALL TO PUBLIC
        USING (owner_id = app_private.current_user_id())
        WITH CHECK (owner_id = app_private.current_user_id())
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_private.consume_owner_daily_quota(
            requested_quota text, requested_limit integer
        ) RETURNS boolean
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app_private
        AS $$
        DECLARE new_units integer;
        BEGIN
            IF requested_quota <> 'upload'
               OR requested_limit < 1 OR requested_limit > 100 THEN
                RAISE EXCEPTION 'invalid quota request';
            END IF;
            INSERT INTO public.owner_daily_quotas (
                owner_id, usage_date, quota_name, used_units
            ) VALUES (
                app_private.current_user_id(), CURRENT_DATE, requested_quota, 1
            )
            ON CONFLICT (owner_id, usage_date, quota_name) DO UPDATE
            SET used_units = owner_daily_quotas.used_units + 1,
                updated_at = now()
            WHERE owner_daily_quotas.used_units < requested_limit
            RETURNING used_units INTO new_units;
            RETURN new_units IS NOT NULL;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE FUNCTION app_private.consume_app_daily_quota(
            requested_quota text, requested_limit integer
        ) RETURNS boolean
        LANGUAGE plpgsql
        SECURITY DEFINER
        SET search_path = pg_catalog, public, app_private
        AS $$
        DECLARE new_units integer;
        BEGIN
            IF requested_quota <> 'gemini_request'
               OR requested_limit < 1 OR requested_limit > 1000 THEN
                RAISE EXCEPTION 'invalid quota request';
            END IF;
            INSERT INTO public.app_daily_quotas (
                usage_date, quota_name, used_units
            ) VALUES (CURRENT_DATE, requested_quota, 1)
            ON CONFLICT (usage_date, quota_name) DO UPDATE
            SET used_units = app_daily_quotas.used_units + 1,
                updated_at = now()
            WHERE app_daily_quotas.used_units < requested_limit
            RETURNING used_units INTO new_units;
            RETURN new_units IS NOT NULL;
        END
        $$
        """
    )
    op.execute(
        """
        CREATE POLICY app_daily_quotas_function_access ON app_daily_quotas
        FOR ALL TO PUBLIC USING (true) WITH CHECK (true)
        """
    )
    op.execute(
        """
        REVOKE ALL ON FUNCTION
            app_private.consume_owner_daily_quota(text, integer),
            app_private.consume_app_daily_quota(text, integer)
            FROM PUBLIC
        """
    )

    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_roles WHERE rolname = 'shiftmate_maintenance'
            ) THEN
                CREATE ROLE shiftmate_maintenance NOLOGIN;
            END IF;
            GRANT shiftmate_maintenance TO CURRENT_USER;
            GRANT USAGE ON SCHEMA public TO shiftmate_maintenance;
            GRANT SELECT, INSERT, UPDATE ON scheduled_job_runs
                TO shiftmate_maintenance;
            GRANT SELECT, UPDATE, DELETE ON shift_imports, policy_documents,
                calendar_sync_records, owner_daily_quotas, app_daily_quotas,
                tool_audit_logs TO shiftmate_maintenance;
        END
        $$
        """
    )
    for table_name in (
        "scheduled_job_runs",
        "shift_imports",
        "policy_documents",
        "calendar_sync_records",
        "owner_daily_quotas",
        "app_daily_quotas",
        "tool_audit_logs",
    ):
        op.execute(
            f"""
            CREATE POLICY {table_name}_maintenance ON {table_name}
            FOR ALL TO shiftmate_maintenance USING (true) WITH CHECK (true)
            """
        )

    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'authenticated') THEN
                GRANT SELECT, INSERT, UPDATE ON owner_daily_quotas TO authenticated;
                GRANT EXECUTE ON FUNCTION
                    app_private.consume_owner_daily_quota(text, integer),
                    app_private.consume_app_daily_quota(text, integer)
                    TO authenticated;
            END IF;
        END
        $$
        """
    )


def downgrade() -> None:
    for table_name in (
        "scheduled_job_runs",
        "shift_imports",
        "policy_documents",
        "calendar_sync_records",
        "tool_audit_logs",
    ):
        op.execute(f"DROP POLICY {table_name}_maintenance ON {table_name}")
    op.execute("DROP FUNCTION app_private.consume_app_daily_quota(text, integer)")
    op.execute("DROP FUNCTION app_private.consume_owner_daily_quota(text, integer)")
    op.drop_table("app_daily_quotas")
    op.drop_table("owner_daily_quotas")
    op.execute(
        """
        REVOKE ALL PRIVILEGES ON scheduled_job_runs, shift_imports,
            policy_documents, calendar_sync_records, tool_audit_logs
            FROM shiftmate_maintenance;
        REVOKE USAGE ON SCHEMA public FROM shiftmate_maintenance;
        """
    )
    op.execute("DROP ROLE IF EXISTS shiftmate_maintenance")

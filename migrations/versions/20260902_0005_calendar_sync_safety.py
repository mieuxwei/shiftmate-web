"""Make Calendar connections and shift sync records idempotent.

Revision ID: 20260902_0005
Revises: 20260902_0004
Create Date: 2026-09-02
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260902_0005"
down_revision: str | None = "20260902_0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_calendar_connections_owner",
        "calendar_connections",
        ["owner_id"],
    )
    op.create_unique_constraint(
        "uq_calendar_sync_records_owner_shift",
        "calendar_sync_records",
        ["owner_id", "shift_id"],
    )
    op.drop_constraint(
        "fk_calendar_sync_records_shift_owner",
        "calendar_sync_records",
        type_="foreignkey",
    )
    op.alter_column("calendar_sync_records", "shift_id", nullable=True)
    op.create_foreign_key(
        "fk_calendar_sync_records_shift_owner",
        "calendar_sync_records",
        "shifts",
        ["shift_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.drop_constraint(
        "ck_calendar_sync_records_status",
        "calendar_sync_records",
        type_="check",
    )
    op.create_check_constraint(
        "ck_calendar_sync_records_status",
        "calendar_sync_records",
        "status IN ('pending', 'synced', 'failed', 'pending_delete', 'deleted')",
    )


def downgrade() -> None:
    op.execute("DELETE FROM calendar_sync_records WHERE shift_id IS NULL")
    op.drop_constraint(
        "ck_calendar_sync_records_status",
        "calendar_sync_records",
        type_="check",
    )
    op.create_check_constraint(
        "ck_calendar_sync_records_status",
        "calendar_sync_records",
        "status IN ('pending', 'synced', 'failed', 'deleted')",
    )
    op.drop_constraint(
        "fk_calendar_sync_records_shift_owner",
        "calendar_sync_records",
        type_="foreignkey",
    )
    op.alter_column("calendar_sync_records", "shift_id", nullable=False)
    op.create_foreign_key(
        "fk_calendar_sync_records_shift_owner",
        "calendar_sync_records",
        "shifts",
        ["shift_id", "owner_id"],
        ["id", "owner_id"],
        ondelete="CASCADE",
    )
    op.drop_constraint(
        "uq_calendar_sync_records_owner_shift",
        "calendar_sync_records",
        type_="unique",
    )
    op.drop_constraint(
        "uq_calendar_connections_owner",
        "calendar_connections",
        type_="unique",
    )

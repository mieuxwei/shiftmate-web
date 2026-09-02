"""Add the idempotent import-item commit link.

Revision ID: 20260902_0003
Revises: 20260902_0002
Create Date: 2026-09-02
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260902_0003"
down_revision: str | None = "20260902_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "shift_import_items",
        sa.Column("item_index", sa.Integer(), nullable=True),
    )
    op.execute(
        """
        WITH indexed AS (
            SELECT id, row_number() OVER (
                PARTITION BY import_id ORDER BY created_at, id
            ) - 1 AS item_index
            FROM shift_import_items
        )
        UPDATE shift_import_items AS item
        SET item_index = indexed.item_index
        FROM indexed WHERE item.id = indexed.id
        """
    )
    op.alter_column("shift_import_items", "item_index", nullable=False)
    op.create_check_constraint(
        "ck_shift_import_items_item_index",
        "shift_import_items",
        "item_index >= 0",
    )
    op.create_unique_constraint(
        "uq_shift_import_items_import_index",
        "shift_import_items",
        ["import_id", "item_index"],
    )
    op.add_column(
        "shift_import_items",
        sa.Column("committed_shift_id", postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.create_foreign_key(
        "fk_shift_import_items_committed_shift",
        "shift_import_items",
        "shifts",
        ["committed_shift_id"],
        ["id"],
        ondelete="SET NULL",
    )
    op.create_unique_constraint(
        "uq_shift_import_items_committed_shift",
        "shift_import_items",
        ["committed_shift_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_shift_import_items_committed_shift",
        "shift_import_items",
        type_="unique",
    )
    op.drop_constraint(
        "fk_shift_import_items_committed_shift",
        "shift_import_items",
        type_="foreignkey",
    )
    op.drop_column("shift_import_items", "committed_shift_id")
    op.drop_constraint(
        "uq_shift_import_items_import_index",
        "shift_import_items",
        type_="unique",
    )
    op.drop_constraint(
        "ck_shift_import_items_item_index",
        "shift_import_items",
        type_="check",
    )
    op.drop_column("shift_import_items", "item_index")

"""add verifying run status

Build Claims and Challenge are new visible phases between research and
synthesis, so the report needs a status to sit in while they run.

Revision ID: f1c2a7d94b30
Revises: 883ba7004106
Create Date: 2026-09-29
"""

from alembic import op

revision = "f1c2a7d94b30"
down_revision = "883ba7004106"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Postgres cannot use a new enum value in the same transaction that adds it,
    # hence the autocommit block.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE run_status_enum ADD VALUE IF NOT EXISTS 'verifying'")


def downgrade() -> None:
    # Enum values cannot be removed in place; recreating the type would fail if
    # any row already holds 'verifying', so downgrade is intentionally a no-op.
    # Downgrading this migration would otherwise silently drop the status of any
    # report that reached the verification stage.
    pass

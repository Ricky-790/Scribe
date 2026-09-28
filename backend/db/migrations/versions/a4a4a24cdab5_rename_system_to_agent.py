"""Rename system to agent

Revision ID: a4a4a24cdab5
Revises: 3ed0a01e969c
Create Date: 2026-08-17 21:28:39.448335

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "a4a4a24cdab5"
down_revision: Union[str, Sequence[str], None] = "3ed0a01e969c"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # PostgreSQL requires the new enum value to be committed
    # before it can be used.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE message_roles_enum ADD VALUE IF NOT EXISTS 'Agent'")

    # Now Agent is usable.
    op.execute("UPDATE messages SET role = 'Agent' WHERE role = 'System'")

    # PostgreSQL cannot remove an enum value directly.
    # Temporarily convert the column to TEXT.
    op.execute(
        """
        ALTER TABLE messages
        ALTER COLUMN role TYPE TEXT
        USING role::TEXT
        """
    )

    # Remove the old enum type.
    op.execute("DROP TYPE message_roles_enum")

    # Recreate it without System.
    op.execute(
        """
        CREATE TYPE message_roles_enum AS ENUM ('User', 'Agent')
        """
    )

    # Convert the column back.
    op.execute(
        """
        ALTER TABLE messages
        ALTER COLUMN role TYPE message_roles_enum
        USING role::message_roles_enum
        """
    )


def downgrade() -> None:
    # Same issue in reverse: System must be committed
    # before it can be used in UPDATE.
    with op.get_context().autocommit_block():
        op.execute("ALTER TYPE message_roles_enum ADD VALUE IF NOT EXISTS 'System'")

    op.execute("UPDATE messages SET role = 'System' WHERE role = 'Agent'")

    op.execute(
        """
        ALTER TABLE messages
        ALTER COLUMN role TYPE TEXT
        USING role::TEXT
        """
    )

    op.execute("DROP TYPE message_roles_enum")

    op.execute(
        """
        CREATE TYPE message_roles_enum AS ENUM ('User', 'System')
        """
    )

    op.execute(
        """
        ALTER TABLE messages
        ALTER COLUMN role TYPE message_roles_enum
        USING role::message_roles_enum
        """
    )

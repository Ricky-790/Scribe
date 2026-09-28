"""Bring back simple ques

Revision ID: c70ef5169ac7
Revises: a4a4a24cdab5
Create Date: 2026-08-17 22:33:50.799462

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "c70ef5169ac7"
down_revision: Union[str, Sequence[str], None] = "a4a4a24cdab5"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.get_context().autocommit_block():
        op.execute(
            """
            ALTER TYPE intent_enum
            ADD VALUE IF NOT EXISTS 'simple_question'
            """
        )


def downgrade() -> None:
    # PostgreSQL cannot remove an enum value directly, so recreate
    # the enum without simple_question.

    op.execute(
        """
        ALTER TABLE user_reports
        ALTER COLUMN intent TYPE TEXT
        USING intent::TEXT
        """
    )

    op.execute("DROP TYPE intent_enum")

    op.execute(
        """
        CREATE TYPE intent_enum AS ENUM (
            'greeting',
            'research_topic',
            'unsupported'
        )
        """
    )

    op.execute(
        """
        ALTER TABLE user_reports
        ALTER COLUMN intent TYPE intent_enum
        USING intent::intent_enum
        """
    )

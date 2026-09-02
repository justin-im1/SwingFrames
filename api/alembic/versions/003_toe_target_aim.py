"""toe-line + target aim

Revision ID: 003
Revises: 002
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "003"
down_revision: Union[str, None] = "002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TYPE aim_method ADD VALUE IF NOT EXISTS 'toe_target'")
    op.add_column(
        "aim_measurements",
        sa.Column("target", postgresql.JSONB(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("aim_measurements", "target")

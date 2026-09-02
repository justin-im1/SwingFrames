"""drop aim and calibration tables

Revision ID: 004
Revises: 003
Create Date: 2026-08-27
"""

from typing import Sequence, Union

from alembic import op

revision: str = "004"
down_revision: Union[str, None] = "003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("ix_aim_measurements_swing_id", table_name="aim_measurements")
    op.drop_table("aim_measurements")
    op.drop_table("calibrations")
    op.execute("DROP TYPE IF EXISTS aim_method")
    op.execute("DROP TYPE IF EXISTS camera_view")


def downgrade() -> None:
    pass

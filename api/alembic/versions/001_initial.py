"""initial schema

Revision ID: 001
Revises:
Create Date: 2026-08-26
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    view_class = postgresql.ENUM(
        "down_the_line", "face_on", "unknown", name="view_class"
    )
    swing_status = postgresql.ENUM(
        "uploaded", "processing", "ready", "failed", name="swing_status"
    )
    handedness = postgresql.ENUM("right", "left", name="handedness")
    view_class.create(op.get_bind(), checkfirst=True)
    swing_status.create(op.get_bind(), checkfirst=True)
    handedness.create(op.get_bind(), checkfirst=True)

    op.create_table(
        "users",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_table(
        "sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("label", sa.String(200), nullable=True),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"])
    op.create_table(
        "swings",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "session_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("sessions.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("source_fps", sa.Float(), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column(
            "view_class",
            postgresql.ENUM(
                "down_the_line", "face_on", "unknown", name="view_class", create_type=False
            ),
            nullable=False,
            server_default="unknown",
        ),
        sa.Column("view_confidence", sa.Float(), nullable=True),
        sa.Column(
            "quality_flags",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("is_usable", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "status",
            postgresql.ENUM(
                "uploaded",
                "processing",
                "ready",
                "failed",
                name="swing_status",
                create_type=False,
            ),
            nullable=False,
            server_default="uploaded",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column(
            "handedness",
            postgresql.ENUM("right", "left", name="handedness", create_type=False),
            nullable=False,
            server_default="right",
        ),
        sa.Column(
            "view_flagged_wrong",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.create_index("ix_swings_session_id", "swings", ["session_id"])
    op.create_table(
        "swing_features",
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            primary_key=True,
        ),
        sa.Column("timestamps", postgresql.JSONB(), nullable=False),
        sa.Column("pelvis_rotation", postgresql.JSONB(), nullable=True),
        sa.Column("torso_rotation", postgresql.JSONB(), nullable=True),
        sa.Column("lead_arm_angle", postgresql.JSONB(), nullable=True),
        sa.Column("wrist_position", postgresql.JSONB(), nullable=True),
        sa.Column("head_position", postgresql.JSONB(), nullable=True),
        sa.Column("mean_visibility", postgresql.JSONB(), nullable=True),
        sa.Column("debug_skeleton", postgresql.JSONB(), nullable=True),
    )
    op.create_table(
        "swing_phases",
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            primary_key=True,
        ),
        sa.Column("address_idx", sa.Integer(), nullable=True),
        sa.Column("top_idx", sa.Integer(), nullable=True),
        sa.Column("impact_idx", sa.Integer(), nullable=True),
        sa.Column("finish_idx", sa.Integer(), nullable=True),
        sa.Column("segmentation_confidence", sa.Float(), nullable=True),
    )
    op.create_table(
        "swing_metrics",
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            primary_key=True,
        ),
        sa.Column("backswing_duration_s", sa.Float(), nullable=True),
        sa.Column("downswing_duration_s", sa.Float(), nullable=True),
        sa.Column("tempo_ratio", sa.Float(), nullable=True),
        sa.Column("pelvis_peak_time_s", sa.Float(), nullable=True),
        sa.Column("torso_peak_time_s", sa.Float(), nullable=True),
        sa.Column("arm_peak_time_s", sa.Float(), nullable=True),
        sa.Column("sequence_order_correct", sa.Boolean(), nullable=True),
        sa.Column("pelvis_torso_gap_ms", sa.Float(), nullable=True),
        sa.Column("torso_arm_gap_ms", sa.Float(), nullable=True),
        sa.Column("peak_magnitude_ratios", postgresql.JSONB(), nullable=True),
        sa.Column(
            "unreliable_metrics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
    )
    op.create_table(
        "comparisons",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "swing_a_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            nullable=False,
        ),
        sa.Column(
            "swing_b_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.Column("dtw_distance", sa.Float(), nullable=True),
        sa.Column("dtw_normalized_distance", sa.Float(), nullable=True),
        sa.Column("warping_path", postgresql.JSONB(), nullable=True),
        sa.Column("timing_divergence", postgresql.JSONB(), nullable=True),
        sa.Column(
            "positional_comparable",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )


def downgrade() -> None:
    op.drop_table("comparisons")
    op.drop_table("swing_metrics")
    op.drop_table("swing_phases")
    op.drop_table("swing_features")
    op.drop_table("swings")
    op.drop_table("sessions")
    op.drop_table("users")
    op.execute("DROP TYPE IF EXISTS handedness")
    op.execute("DROP TYPE IF EXISTS swing_status")
    op.execute("DROP TYPE IF EXISTS view_class")

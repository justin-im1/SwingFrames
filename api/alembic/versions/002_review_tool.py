"""replace pose schema with review-tool schema

Revision ID: 002
Revises: 001
Create Date: 2026-08-27
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "002"
down_revision: Union[str, None] = "001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_table("comparisons")
    op.drop_table("swing_metrics")
    op.drop_table("swing_phases")
    op.drop_table("swing_features")
    op.drop_table("swings")

    op.execute("DROP TYPE IF EXISTS view_class")
    op.execute("DROP TYPE IF EXISTS swing_status")
    op.execute("DROP TYPE IF EXISTS handedness")

    transcode_status = postgresql.ENUM(
        "pending", "ready", "failed", name="transcode_status"
    )
    annotation_kind = postgresql.ENUM(
        "line", "angle", "circle", "freehand", name="annotation_kind"
    )
    camera_view = postgresql.ENUM(
        "face_on", "down_the_line", name="camera_view"
    )
    aim_method = postgresql.ENUM("toe_stick", "heel_taps", name="aim_method")
    outcome_result = postgresql.ENUM(
        "straight",
        "slice",
        "hook",
        "pull",
        "push",
        "thin",
        "fat",
        "topped",
        name="outcome_result",
    )
    sync_mode = postgresql.ENUM(
        "independent", "offset", "normalized", name="sync_mode"
    )
    transcode_status.create(op.get_bind(), checkfirst=True)
    annotation_kind.create(op.get_bind(), checkfirst=True)
    camera_view.create(op.get_bind(), checkfirst=True)
    aim_method.create(op.get_bind(), checkfirst=True)
    outcome_result.create(op.get_bind(), checkfirst=True)
    sync_mode.create(op.get_bind(), checkfirst=True)

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
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("filename", sa.String(500), nullable=True),
        sa.Column("storage_path", sa.String(1000), nullable=True),
        sa.Column("width", sa.Integer(), nullable=True),
        sa.Column("height", sa.Integer(), nullable=True),
        sa.Column("fps", sa.Float(), nullable=True),
        sa.Column("frame_count", sa.Integer(), nullable=True),
        sa.Column("duration_s", sa.Float(), nullable=True),
        sa.Column("distinct_frame_ratio", sa.Float(), nullable=True),
        sa.Column(
            "transcode_status",
            postgresql.ENUM(
                "pending", "ready", "failed", name="transcode_status", create_type=False
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("error_message", sa.Text(), nullable=True),
    )
    op.create_index("ix_swings_session_id", "swings", ["session_id"])

    op.create_table(
        "annotations",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            nullable=False,
        ),
        sa.Column("frame", sa.Integer(), nullable=False),
        sa.Column(
            "kind",
            postgresql.ENUM(
                "line",
                "angle",
                "circle",
                "freehand",
                name="annotation_kind",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("points", postgresql.JSONB(), nullable=False),
        sa.Column("style", postgresql.JSONB(), nullable=True),
        sa.Column("label", sa.String(200), nullable=True),
        sa.Column("sticky", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_annotations_swing_id", "annotations", ["swing_id"])

    op.create_table(
        "calibrations",
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            primary_key=True,
        ),
        sa.Column("frame", sa.Integer(), nullable=False),
        sa.Column("homography", postgresql.JSONB(), nullable=False),
        sa.Column("stick_length_m", sa.Float(), nullable=False),
        sa.Column("stick_separation_m", sa.Float(), nullable=False),
        sa.Column("residual_px", sa.Float(), nullable=False),
        sa.Column(
            "view",
            postgresql.ENUM(
                "face_on", "down_the_line", name="camera_view", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("calib_lines", postgresql.JSONB(), nullable=False),
        sa.Column("toe_line", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )

    op.create_table(
        "aim_measurements",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            nullable=False,
        ),
        sa.Column(
            "method",
            postgresql.ENUM(
                "toe_stick", "heel_taps", name="aim_method", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "view",
            postgresql.ENUM(
                "face_on", "down_the_line", name="camera_view", create_type=False
            ),
            nullable=False,
        ),
        sa.Column("heel_a", postgresql.JSONB(), nullable=True),
        sa.Column("heel_b", postgresql.JSONB(), nullable=True),
        sa.Column("toe_line", postgresql.JSONB(), nullable=True),
        sa.Column("feet_angle_deg", sa.Float(), nullable=True),
        sa.Column("error_band_deg", sa.Float(), nullable=True),
        sa.Column("verdict", sa.String(32), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_aim_measurements_swing_id", "aim_measurements", ["swing_id"])

    op.create_table(
        "outcomes",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "swing_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("swings.id"),
            nullable=False,
        ),
        sa.Column(
            "result",
            postgresql.ENUM(
                "straight",
                "slice",
                "hook",
                "pull",
                "push",
                "thin",
                "fat",
                "topped",
                name="outcome_result",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("swing_id", name="uq_outcomes_swing_id"),
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
            "sync_mode",
            postgresql.ENUM(
                "independent",
                "offset",
                "normalized",
                name="sync_mode",
                create_type=False,
            ),
            nullable=False,
            server_default="independent",
        ),
        sa.Column("anchor_a", sa.Integer(), nullable=True),
        sa.Column("anchor_b", sa.Integer(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )


def downgrade() -> None:
    raise NotImplementedError("Pose schema is not restored.")

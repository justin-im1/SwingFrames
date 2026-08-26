from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ViewClass(str, enum.Enum):
    down_the_line = "down_the_line"
    face_on = "face_on"
    unknown = "unknown"


class SwingStatus(str, enum.Enum):
    uploaded = "uploaded"
    processing = "processing"
    ready = "ready"
    failed = "failed"


class Handedness(str, enum.Enum):
    right = "right"
    left = "left"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    sessions: Mapped[list[Session]] = relationship(back_populates="user")


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)

    user: Mapped[User] = relationship(back_populates="sessions")
    swings: Mapped[list[Swing]] = relationship(back_populates="session")


class Swing(Base):
    __tablename__ = "swings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("sessions.id"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    source_fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    view_class: Mapped[ViewClass] = mapped_column(
        Enum(ViewClass, name="view_class"), default=ViewClass.unknown, nullable=False
    )
    view_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_flags: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)
    is_usable: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    status: Mapped[SwingStatus] = mapped_column(
        Enum(SwingStatus, name="swing_status"),
        default=SwingStatus.uploaded,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    handedness: Mapped[Handedness] = mapped_column(
        Enum(Handedness, name="handedness"), default=Handedness.right, nullable=False
    )
    view_flagged_wrong: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    session: Mapped[Session] = relationship(back_populates="swings")
    features: Mapped[SwingFeatures | None] = relationship(
        back_populates="swing", uselist=False
    )
    phases: Mapped[SwingPhases | None] = relationship(
        back_populates="swing", uselist=False
    )
    metrics: Mapped[SwingMetrics | None] = relationship(
        back_populates="swing", uselist=False
    )


class SwingFeatures(Base):
    __tablename__ = "swing_features"

    swing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), primary_key=True
    )
    timestamps: Mapped[list] = mapped_column(JSONB, nullable=False)
    pelvis_rotation: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    torso_rotation: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    lead_arm_angle: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    wrist_position: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    head_position: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    mean_visibility: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    debug_skeleton: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    swing: Mapped[Swing] = relationship(back_populates="features")


class SwingPhases(Base):
    __tablename__ = "swing_phases"

    swing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), primary_key=True
    )
    address_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    top_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    impact_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    finish_idx: Mapped[int | None] = mapped_column(Integer, nullable=True)
    segmentation_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)

    swing: Mapped[Swing] = relationship(back_populates="phases")


class SwingMetrics(Base):
    __tablename__ = "swing_metrics"

    swing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), primary_key=True
    )
    backswing_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    downswing_duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    tempo_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    pelvis_peak_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    torso_peak_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    arm_peak_time_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    sequence_order_correct: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    pelvis_torso_gap_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    torso_arm_gap_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    peak_magnitude_ratios: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    unreliable_metrics: Mapped[list] = mapped_column(JSONB, default=list, nullable=False)

    swing: Mapped[Swing] = relationship(back_populates="metrics")


class Comparison(Base):
    __tablename__ = "comparisons"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    swing_a_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), nullable=False
    )
    swing_b_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    dtw_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    dtw_normalized_distance: Mapped[float | None] = mapped_column(Float, nullable=True)
    warping_path: Mapped[list | None] = mapped_column(JSONB, nullable=True)
    timing_divergence: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    positional_comparable: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )

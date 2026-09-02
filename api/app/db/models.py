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


class TranscodeStatus(str, enum.Enum):
    pending = "pending"
    ready = "ready"
    failed = "failed"


class AnnotationKind(str, enum.Enum):
    line = "line"
    angle = "angle"
    circle = "circle"
    freehand = "freehand"


class OutcomeResult(str, enum.Enum):
    straight = "straight"
    slice = "slice"
    hook = "hook"
    pull = "pull"
    push = "push"
    thin = "thin"
    fat = "fat"
    topped = "topped"


class SyncMode(str, enum.Enum):
    independent = "independent"
    offset = "offset"
    normalized = "normalized"


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
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    filename: Mapped[str | None] = mapped_column(String(500), nullable=True)
    storage_path: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    fps: Mapped[float | None] = mapped_column(Float, nullable=True)
    frame_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_s: Mapped[float | None] = mapped_column(Float, nullable=True)
    distinct_frame_ratio: Mapped[float | None] = mapped_column(Float, nullable=True)
    transcode_status: Mapped[TranscodeStatus] = mapped_column(
        Enum(TranscodeStatus, name="transcode_status"),
        default=TranscodeStatus.pending,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    session: Mapped[Session] = relationship(back_populates="swings")
    annotations: Mapped[list[Annotation]] = relationship(back_populates="swing")
    outcomes: Mapped[list[Outcome]] = relationship(back_populates="swing")


class Annotation(Base):
    __tablename__ = "annotations"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    swing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), nullable=False, index=True
    )
    frame: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[AnnotationKind] = mapped_column(
        Enum(AnnotationKind, name="annotation_kind"), nullable=False
    )
    points: Mapped[list] = mapped_column(JSONB, nullable=False)
    style: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    label: Mapped[str | None] = mapped_column(String(200), nullable=True)
    sticky: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    swing: Mapped[Swing] = relationship(back_populates="annotations")


class Outcome(Base):
    __tablename__ = "outcomes"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    swing_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("swings.id"), nullable=False, unique=True
    )
    result: Mapped[OutcomeResult] = mapped_column(
        Enum(OutcomeResult, name="outcome_result"), nullable=False
    )
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    swing: Mapped[Swing] = relationship(back_populates="outcomes")


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
    sync_mode: Mapped[SyncMode] = mapped_column(
        Enum(SyncMode, name="sync_mode"),
        default=SyncMode.independent,
        nullable=False,
    )
    anchor_a: Mapped[int | None] = mapped_column(Integer, nullable=True)
    anchor_b: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

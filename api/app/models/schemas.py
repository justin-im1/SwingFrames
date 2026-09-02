from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

TranscodeStatus = Literal["pending", "ready", "failed"]
AnnotationKind = Literal["line", "angle", "circle", "freehand"]
OutcomeResult = Literal[
    "straight", "slice", "hook", "pull", "push", "thin", "fat", "topped"
]
SyncMode = Literal["independent", "offset", "normalized"]


class Point(BaseModel):
    x: float
    y: float


class SessionCreate(BaseModel):
    label: str | None = None


class SessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    label: str | None = None
    swing_count: int = 0


class SwingCreateResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    transcode_status: TranscodeStatus


class SwingOut(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
    label: str | None = None
    filename: str | None = None
    width: int | None = None
    height: int | None = None
    fps: float | None = None
    frame_count: int | None = None
    duration_s: float | None = None
    distinct_frame_ratio: float | None = None
    transcode_status: TranscodeStatus
    error_message: str | None = None
    low_distinct_frames: bool = False


class SessionDetail(SessionOut):
    swings: list[SwingOut] = Field(default_factory=list)


class AnnotationCreate(BaseModel):
    frame: int
    kind: AnnotationKind
    points: list[Point]
    style: dict[str, Any] | None = None
    label: str | None = None
    sticky: bool = False


class AnnotationOut(BaseModel):
    id: uuid.UUID
    swing_id: uuid.UUID
    frame: int
    kind: AnnotationKind
    points: list[Point]
    style: dict[str, Any] | None = None
    label: str | None = None
    sticky: bool
    created_at: datetime


class AnnotationCopy(BaseModel):
    source_id: uuid.UUID
    target_frame: int = 0
    annotation_ids: list[uuid.UUID] | None = None


class OutcomeCreate(BaseModel):
    result: OutcomeResult
    note: str | None = None


class OutcomeOut(BaseModel):
    id: uuid.UUID
    swing_id: uuid.UUID
    result: OutcomeResult
    note: str | None = None
    created_at: datetime


class InsightLine(BaseModel):
    text: str
    n: int
    outcome: OutcomeResult | None = None


class InsightsOut(BaseModel):
    session_id: uuid.UUID
    tagged_n: int
    ready: bool
    message: str
    lines: list[InsightLine] = Field(default_factory=list)


class ComparisonCreate(BaseModel):
    swing_a_id: uuid.UUID
    swing_b_id: uuid.UUID
    sync_mode: SyncMode = "independent"
    anchor_a: int | None = None
    anchor_b: int | None = None


class ComparisonOut(BaseModel):
    id: uuid.UUID
    swing_a_id: uuid.UUID
    swing_b_id: uuid.UUID
    sync_mode: SyncMode
    anchor_a: int | None = None
    anchor_b: int | None = None
    created_at: datetime

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ViewClass = Literal["down_the_line", "face_on", "unknown"]
SwingStatus = Literal["uploaded", "processing", "ready", "failed"]
Handedness = Literal["right", "left"]


class QualityFlag(BaseModel):
    code: str
    severity: Literal["info", "warning", "error"]
    message: str
    details: dict[str, Any] = Field(default_factory=dict)


class SwingCreateResponse(BaseModel):
    id: uuid.UUID
    status: SwingStatus
    session_id: uuid.UUID


class SwingSummary(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    created_at: datetime
    status: SwingStatus
    source_fps: float | None = None
    frame_count: int | None = None
    duration_s: float | None = None
    view_class: ViewClass
    view_confidence: float | None = None
    quality_flags: list[QualityFlag] = Field(default_factory=list)
    is_usable: bool = True
    error_message: str | None = None
    handedness: Handedness = "right"
    view_flagged_wrong: bool = False


class PhaseBoundary(BaseModel):
    address_idx: int | None = None
    top_idx: int | None = None
    impact_idx: int | None = None
    finish_idx: int | None = None
    segmentation_confidence: float | None = None


class SwingMetricsOut(BaseModel):
    swing_id: uuid.UUID
    backswing_duration_s: float | None = None
    downswing_duration_s: float | None = None
    tempo_ratio: float | None = None
    pelvis_peak_time_s: float | None = None
    torso_peak_time_s: float | None = None
    arm_peak_time_s: float | None = None
    sequence_order_correct: bool | None = None
    pelvis_torso_gap_ms: float | None = None
    torso_arm_gap_ms: float | None = None
    peak_magnitude_ratios: dict[str, float] | None = None
    unreliable_metrics: list[str] = Field(default_factory=list)
    phases: PhaseBoundary | None = None


class SwingFeaturesOut(BaseModel):
    swing_id: uuid.UUID
    timestamps: list[float]
    pelvis_rotation: list[float | None] | None = None
    torso_rotation: list[float | None] | None = None
    lead_arm_angle: list[float | None] | None = None
    pelvis_velocity: list[float | None] | None = None
    torso_velocity: list[float | None] | None = None
    arm_velocity: list[float | None] | None = None
    wrist_position: list[list[float | None]] | None = None
    head_position: list[list[float | None]] | None = None
    mean_visibility: list[float | None] | None = None
    debug_skeleton: dict[str, Any] | None = None


class ComparisonCreate(BaseModel):
    swing_a_id: uuid.UUID
    swing_b_id: uuid.UUID


class PhaseDurationRatio(BaseModel):
    name: str
    swing_a_s: float | None = None
    swing_b_s: float | None = None
    ratio: float | None = None
    percent_longer_b: float | None = None
    message: str


class TimingDivergence(BaseModel):
    deviation_curve: list[dict[str, float]]
    phase_duration_ratios: list[PhaseDurationRatio]


class ComparisonOut(BaseModel):
    id: uuid.UUID
    swing_a_id: uuid.UUID
    swing_b_id: uuid.UUID
    created_at: datetime
    dtw_distance: float | None = None
    dtw_normalized_distance: float | None = None
    warping_path: list[list[int]] | None = None
    timing_divergence: TimingDivergence | None = None
    positional_comparable: bool
    disabled_reason: str | None = None


class SessionOut(BaseModel):
    id: uuid.UUID
    user_id: uuid.UUID
    created_at: datetime
    label: str | None = None
    swing_count: int = 0


class SessionDetail(SessionOut):
    swings: list[SwingSummary] = Field(default_factory=list)


class ConsistencyMetric(BaseModel):
    name: str
    mean: float | None = None
    std: float | None = None
    cv: float | None = None
    n: int
    values: list[float | None]


class ConsistencyOut(BaseModel):
    session_id: uuid.UUID
    n: int
    usable_n: int
    ready: bool
    message: str
    metrics: list[ConsistencyMetric] = Field(default_factory=list)
    least_repeatable: str | None = None


class ProBenchmark(BaseModel):
    id: str
    name: str
    tempo_ratio: float
    backswing_s: float
    downswing_s: float
    source: str


class SessionCreate(BaseModel):
    label: str | None = None


class FlagViewBody(BaseModel):
    note: str | None = None

"""Pipeline orchestrator: video → features, phases, metrics. Always deletes the file."""

from __future__ import annotations

import logging
import os
import uuid
from dataclasses import dataclass, field

import numpy as np
from sqlalchemy.orm import Session

from app.db.models import (
    Handedness,
    Swing,
    SwingFeatures,
    SwingMetrics,
    SwingPhases,
    SwingStatus,
    ViewClass,
)
from app.pipeline.analyze import AnalyzeResult, analyze_swing, downsample_skeleton
from app.pipeline.clean import clean_landmarks
from app.pipeline.ingest import IngestError, iter_frames, read_meta
from app.pipeline.landmarks import LEFT_WRIST, NOSE, nan_to_none, nested_nan_to_none
from app.pipeline.normalize import normalize_landmarks
from app.pipeline.pose import extract_pose
from app.pipeline.segment import segment_swing
from app.pipeline.view import classify_view

logger = logging.getLogger(__name__)


@dataclass
class PipelineResult:
    fps: float
    frame_count: int
    duration_s: float
    timestamps: np.ndarray
    xyz: np.ndarray
    vis: np.ndarray
    view_class: str
    view_confidence: float
    handedness: str
    address_idx: int
    top_idx: int
    impact_idx: int
    finish_idx: int
    segmentation_confidence: float
    analysis: AnalyzeResult
    quality_flags: list[dict] = field(default_factory=list)
    is_usable: bool = True


def run_pipeline(
    xyz: np.ndarray,
    vis: np.ndarray,
    fps: float,
    image_lm: np.ndarray | None = None,
    handedness_hint: str | None = None,
) -> PipelineResult:
    flags: list[dict] = []
    cleaned = clean_landmarks(xyz, vis, fps, image_lm=image_lm)
    flags.extend(cleaned.quality_flags)

    norm = normalize_landmarks(
        cleaned.xyz, cleaned.timestamps, vis=cleaned.vis, handedness_hint=handedness_hint
    )
    flags.extend(norm.quality_flags)

    address_for_view = norm.address_idx
    if cleaned.image_lm is not None:
        view = classify_view(cleaned.image_lm, address_for_view)
    else:
        from app.pipeline.view import ViewResult

        view = ViewResult("unknown", 0.0, float("nan"), [])
    flags.extend(view.quality_flags)

    phases = segment_swing(norm.xyz, cleaned.timestamps)
    flags.extend(phases.quality_flags)

    analysis = analyze_swing(
        norm.xyz,
        cleaned.timestamps,
        phases.address_idx,
        phases.top_idx,
        phases.impact_idx,
        phases.finish_idx,
    )
    flags.extend(analysis.quality_flags)

    is_usable = phases.confidence >= 0.55
    if not is_usable:
        flags.append(
            {
                "code": "unusable",
                "severity": "error",
                "message": "Segmentation confidence is too low to treat this swing as usable.",
                "details": {"confidence": phases.confidence},
            }
        )

    duration_s = float(cleaned.timestamps[-1]) if cleaned.timestamps.size else 0.0
    return PipelineResult(
        fps=fps,
        frame_count=int(xyz.shape[0]),
        duration_s=duration_s,
        timestamps=cleaned.timestamps,
        xyz=norm.xyz,
        vis=cleaned.vis,
        view_class=view.view_class,
        view_confidence=view.confidence,
        handedness=norm.handedness,
        address_idx=phases.address_idx,
        top_idx=phases.top_idx,
        impact_idx=phases.impact_idx,
        finish_idx=phases.finish_idx,
        segmentation_confidence=phases.confidence,
        analysis=analysis,
        quality_flags=flags,
        is_usable=is_usable,
    )


def persist_pipeline_result(db: Session, swing: Swing, result: PipelineResult) -> None:
    a = result.analysis
    swing.source_fps = result.fps
    swing.frame_count = result.frame_count
    swing.duration_s = result.duration_s
    swing.view_class = ViewClass(result.view_class)
    swing.view_confidence = result.view_confidence
    swing.quality_flags = result.quality_flags
    swing.is_usable = result.is_usable
    swing.handedness = Handedness(result.handedness)
    swing.status = SwingStatus.ready
    swing.error_message = None

    debug = downsample_skeleton(result.xyz, result.timestamps)
    features = SwingFeatures(
        swing_id=swing.id,
        timestamps=[float(t) for t in result.timestamps],
        pelvis_rotation=nan_to_none(a.pelvis_rotation),
        torso_rotation=nan_to_none(a.torso_rotation),
        lead_arm_angle=nan_to_none(a.lead_arm_angle),
        wrist_position=nested_nan_to_none(result.xyz[:, LEFT_WRIST]),
        head_position=nested_nan_to_none(result.xyz[:, NOSE]),
        mean_visibility=nan_to_none(np.nanmean(result.vis, axis=1)),
        debug_skeleton=debug,
    )
    phases = SwingPhases(
        swing_id=swing.id,
        address_idx=result.address_idx,
        top_idx=result.top_idx,
        impact_idx=result.impact_idx,
        finish_idx=result.finish_idx,
        segmentation_confidence=result.segmentation_confidence,
    )
    metrics = SwingMetrics(
        swing_id=swing.id,
        backswing_duration_s=a.backswing_duration_s,
        downswing_duration_s=a.downswing_duration_s,
        tempo_ratio=a.tempo_ratio,
        pelvis_peak_time_s=a.pelvis_peak_time_s,
        torso_peak_time_s=a.torso_peak_time_s,
        arm_peak_time_s=a.arm_peak_time_s,
        sequence_order_correct=a.sequence_order_correct,
        pelvis_torso_gap_ms=a.pelvis_torso_gap_ms,
        torso_arm_gap_ms=a.torso_arm_gap_ms,
        peak_magnitude_ratios=a.peak_magnitude_ratios,
        unreliable_metrics=a.unreliable_metrics,
    )
    db.merge(features)
    db.merge(phases)
    db.merge(metrics)


def process_swing_job(
    swing_id: uuid.UUID,
    video_path: str,
    handedness_hint: str | None = None,
) -> None:
    from app.db.session import SyncSessionLocal

    db = SyncSessionLocal()
    try:
        swing = db.get(Swing, swing_id)
        if swing is None:
            logger.error("Swing %s missing; skipping job.", swing_id)
            return
        swing.status = SwingStatus.processing
        db.commit()

        meta = read_meta(video_path)
        frames = iter_frames(video_path, meta)
        xyz, vis, image_lm = extract_pose(frames)
        used_frames = xyz.shape[0]
        used_fps = meta.fps
        result = run_pipeline(
            xyz, vis, used_fps, image_lm=image_lm, handedness_hint=handedness_hint
        )
        result.quality_flags = list(meta.quality_flags) + result.quality_flags
        result.frame_count = used_frames
        persist_pipeline_result(db, swing, result)
        db.commit()
        logger.info(
            "Swing %s ready. view=%s tempo=%s",
            swing_id,
            result.view_class,
            result.analysis.tempo_ratio,
        )
    except IngestError as exc:
        logger.warning("Ingest rejected swing %s: %s", swing_id, exc)
        swing = db.get(Swing, swing_id)
        if swing is not None:
            swing.status = SwingStatus.failed
            swing.error_message = str(exc)
            swing.quality_flags = [
                {
                    "code": "ingest_rejected",
                    "severity": "error",
                    "message": str(exc),
                    "details": {},
                }
            ]
            db.commit()
    except Exception:
        logger.exception("Pipeline failed for swing %s", swing_id)
        db.rollback()
        swing = db.get(Swing, swing_id)
        if swing is not None:
            swing.status = SwingStatus.failed
            swing.error_message = "Analysis failed. The video was discarded."
            db.commit()
    finally:
        db.close()
        try:
            os.remove(video_path)
        except OSError:
            logger.warning("Could not delete temp video %s", video_path)

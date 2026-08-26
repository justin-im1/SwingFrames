from __future__ import annotations

import tempfile
import uuid
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.db.models import Session, Swing, SwingStatus, User
from app.db.session import get_db
from app.deps import get_client_user
from app.models.schemas import (
    FlagViewBody,
    PhaseBoundary,
    SwingCreateResponse,
    SwingFeaturesOut,
    SwingMetricsOut,
    SwingSummary,
)
from app.pipeline.ingest import IngestError, read_meta
from app.pipeline.run import process_swing_job
from app.pipeline.signal import smooth_then_diff
from app.routers.sessions import swing_summary

router = APIRouter(prefix="/api/swings", tags=["swings"])


async def _get_owned_swing(
    db: AsyncSession, user: User, swing_id: uuid.UUID
) -> Swing:
    result = await db.execute(
        select(Swing)
        .options(
            selectinload(Swing.session),
            selectinload(Swing.features),
            selectinload(Swing.phases),
            selectinload(Swing.metrics),
        )
        .where(Swing.id == swing_id)
    )
    swing = result.scalar_one_or_none()
    if swing is None or swing.session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Swing not found.")
    return swing


@router.post("", response_model=SwingCreateResponse)
async def upload_swing(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session_id: uuid.UUID | None = Form(None),
    handedness: str | None = Form(None),
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingCreateResponse:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty upload.")
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="File exceeds 500 MB.")

    suffix = Path(file.filename or "swing.mp4").suffix or ".mp4"
    tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    tmp.write(data)
    tmp.close()

    try:
        read_meta(tmp.name)
    except IngestError as exc:
        Path(tmp.name).unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    if session_id is not None:
        session = await db.get(Session, session_id)
        if session is None or session.user_id != user.id:
            Path(tmp.name).unlink(missing_ok=True)
            raise HTTPException(status_code=404, detail="Session not found.")
    else:
        session = Session(user_id=user.id, label="Session")
        db.add(session)
        await db.flush()

    swing = Swing(session_id=session.id, status=SwingStatus.uploaded)
    db.add(swing)
    await db.commit()
    await db.refresh(swing)

    hint = handedness if handedness in ("left", "right") else None
    background_tasks.add_task(process_swing_job, swing.id, tmp.name, hint)
    return SwingCreateResponse(id=swing.id, status=swing.status.value, session_id=session.id)


@router.get("/{swing_id}", response_model=SwingSummary)
async def get_swing(
    swing_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingSummary:
    swing = await _get_owned_swing(db, user, swing_id)
    return swing_summary(swing)


@router.post("/{swing_id}/flag-view", response_model=SwingSummary)
async def flag_view(
    swing_id: uuid.UUID,
    body: FlagViewBody,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingSummary:
    """Record that the user thinks the view class is wrong. Does not override gating."""
    swing = await _get_owned_swing(db, user, swing_id)
    swing.view_flagged_wrong = True
    flags = list(swing.quality_flags or [])
    flags.append(
        {
            "code": "view_flagged_wrong",
            "severity": "info",
            "message": body.note
            or "User flagged the detected view class as wrong. The class is not overridden.",
            "details": {},
        }
    )
    swing.quality_flags = flags
    await db.commit()
    await db.refresh(swing)
    return swing_summary(swing)


@router.get("/{swing_id}/metrics", response_model=SwingMetricsOut)
async def get_metrics(
    swing_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingMetricsOut:
    swing = await _get_owned_swing(db, user, swing_id)
    if swing.status != SwingStatus.ready or swing.metrics is None:
        raise HTTPException(status_code=409, detail="Swing is not ready.")
    m = swing.metrics
    p = swing.phases
    return SwingMetricsOut(
        swing_id=swing.id,
        backswing_duration_s=m.backswing_duration_s,
        downswing_duration_s=m.downswing_duration_s,
        tempo_ratio=m.tempo_ratio,
        pelvis_peak_time_s=m.pelvis_peak_time_s,
        torso_peak_time_s=m.torso_peak_time_s,
        arm_peak_time_s=m.arm_peak_time_s,
        sequence_order_correct=m.sequence_order_correct,
        pelvis_torso_gap_ms=m.pelvis_torso_gap_ms,
        torso_arm_gap_ms=m.torso_arm_gap_ms,
        peak_magnitude_ratios=m.peak_magnitude_ratios,
        unreliable_metrics=m.unreliable_metrics or [],
        phases=None
        if p is None
        else PhaseBoundary(
            address_idx=p.address_idx,
            top_idx=p.top_idx,
            impact_idx=p.impact_idx,
            finish_idx=p.finish_idx,
            segmentation_confidence=p.segmentation_confidence,
        ),
    )


@router.get("/{swing_id}/features", response_model=SwingFeaturesOut)
async def get_features(
    swing_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingFeaturesOut:
    swing = await _get_owned_swing(db, user, swing_id)
    if swing.status != SwingStatus.ready or swing.features is None:
        raise HTTPException(status_code=409, detail="Swing is not ready.")
    f = swing.features
    ts = [float(t) for t in f.timestamps]
    dt = (ts[1] - ts[0]) if len(ts) > 1 else 1.0 / 240.0

    def vel(series: list | None) -> list[float | None] | None:
        if not series:
            return None
        import numpy as np

        arr = np.array([np.nan if v is None else v for v in series], dtype=float)
        return [
            None if not np.isfinite(v) else float(v) for v in smooth_then_diff(arr, dt)
        ]

    return SwingFeaturesOut(
        swing_id=swing.id,
        timestamps=ts,
        pelvis_rotation=f.pelvis_rotation,
        torso_rotation=f.torso_rotation,
        lead_arm_angle=f.lead_arm_angle,
        pelvis_velocity=vel(f.pelvis_rotation),
        torso_velocity=vel(f.torso_rotation),
        arm_velocity=vel(f.lead_arm_angle),
        wrist_position=f.wrist_position,
        head_position=f.head_position,
        mean_visibility=f.mean_visibility,
        debug_skeleton=f.debug_skeleton,
    )

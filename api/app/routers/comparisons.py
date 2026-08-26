from __future__ import annotations

import uuid

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Comparison, Swing, SwingStatus, User, ViewClass
from app.db.session import get_db
from app.deps import get_client_user
from app.models.schemas import ComparisonCreate, ComparisonOut, TimingDivergence
from app.pipeline.dtw import deviation_curve, dtw, phase_duration_ratios

router = APIRouter(prefix="/api/comparisons", tags=["comparisons"])


async def _owned_ready(
    db: AsyncSession, user: User, swing_id: uuid.UUID
) -> Swing:
    result = await db.execute(
        select(Swing)
        .options(
            selectinload(Swing.session),
            selectinload(Swing.features),
            selectinload(Swing.phases),
        )
        .where(Swing.id == swing_id)
    )
    swing = result.scalar_one_or_none()
    if swing is None or swing.session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Swing not found.")
    if swing.status != SwingStatus.ready or swing.features is None or swing.phases is None:
        raise HTTPException(status_code=409, detail="Both swings must be finished analyzing.")
    return swing


def _angle_matrix(swing: Swing) -> np.ndarray:
    f = swing.features
    pelvis = np.array([np.nan if v is None else v for v in f.pelvis_rotation], dtype=float)
    torso = np.array([np.nan if v is None else v for v in f.torso_rotation], dtype=float)
    arm = np.array([np.nan if v is None else v for v in f.lead_arm_angle], dtype=float)
    return np.stack([pelvis, torso, arm], axis=1)


@router.post("", response_model=ComparisonOut)
async def create_comparison(
    body: ComparisonCreate,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonOut:
    if body.swing_a_id == body.swing_b_id:
        raise HTTPException(status_code=400, detail="Pick two different swings.")
    a = await _owned_ready(db, user, body.swing_a_id)
    b = await _owned_ready(db, user, body.swing_b_id)

    series_a = _angle_matrix(a)
    series_b = _angle_matrix(b)
    result = dtw(series_a, series_b)

    ts_a = np.array(a.features.timestamps, dtype=float)
    ts_b = np.array(b.features.timestamps, dtype=float)
    phases_a = {
        "address_idx": a.phases.address_idx,
        "top_idx": a.phases.top_idx,
        "impact_idx": a.phases.impact_idx,
        "finish_idx": a.phases.finish_idx,
    }
    ratios = phase_duration_ratios(ts_a, ts_b, result.path, phases_a)
    curve = deviation_curve(result.path, series_a.shape[0], series_b.shape[0])
    # Keep the stored curve manageable.
    if len(curve) > 800:
        step = max(1, len(curve) // 800)
        curve = curve[::step]

    positional = (
        a.view_class == b.view_class and a.view_class != ViewClass.unknown
    )
    disabled_reason = None
    if not positional:
        if a.view_class == ViewClass.unknown or b.view_class == ViewClass.unknown:
            disabled_reason = (
                "Positional overlay is disabled because at least one swing has "
                "an unknown view class."
            )
        else:
            disabled_reason = (
                f"Positional overlay is disabled: swing A is {a.view_class.value}, "
                f"swing B is {b.view_class.value}. Timing comparison is still valid."
            )

    path_list = [[i, j] for i, j in result.path]
    if len(path_list) > 2000:
        step = max(1, len(path_list) // 2000)
        path_list = path_list[::step]

    row = Comparison(
        swing_a_id=a.id,
        swing_b_id=b.id,
        dtw_distance=result.distance,
        dtw_normalized_distance=result.normalized_distance,
        warping_path=path_list,
        timing_divergence={
            "deviation_curve": curve,
            "phase_duration_ratios": ratios,
        },
        positional_comparable=positional,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ComparisonOut(
        id=row.id,
        swing_a_id=row.swing_a_id,
        swing_b_id=row.swing_b_id,
        created_at=row.created_at,
        dtw_distance=row.dtw_distance,
        dtw_normalized_distance=row.dtw_normalized_distance,
        warping_path=row.warping_path,
        timing_divergence=TimingDivergence.model_validate(row.timing_divergence),
        positional_comparable=row.positional_comparable,
        disabled_reason=disabled_reason,
    )


@router.get("/{comparison_id}", response_model=ComparisonOut)
async def get_comparison(
    comparison_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonOut:
    row = await db.get(Comparison, comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    a = await _owned_ready(db, user, row.swing_a_id)
    _ = await _owned_ready(db, user, row.swing_b_id)
    positional = row.positional_comparable
    disabled_reason = None
    if not positional:
        disabled_reason = (
            "Positional overlay is disabled because the two swings are not in "
            "the same known view class."
        )
    return ComparisonOut(
        id=row.id,
        swing_a_id=row.swing_a_id,
        swing_b_id=row.swing_b_id,
        created_at=row.created_at,
        dtw_distance=row.dtw_distance,
        dtw_normalized_distance=row.dtw_normalized_distance,
        warping_path=row.warping_path,
        timing_divergence=TimingDivergence.model_validate(row.timing_divergence)
        if row.timing_divergence
        else None,
        positional_comparable=positional,
        disabled_reason=disabled_reason,
    )

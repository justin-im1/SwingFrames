from __future__ import annotations

import asyncio
import uuid
from pathlib import Path

import numpy as np
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import (
    AimMeasurement,
    AimMethod,
    Calibration,
    CameraView,
    Outcome,
    OutcomeResult,
    TranscodeStatus,
    User,
)
from app.db.session import get_db
from app.deps import get_client_user, get_swing, require_swing_owner
from app.geometry import (
    LineAssignError,
    assign_lines,
    coarse_verdict,
    detect_stick_lines,
    feet_angle_deg,
    fit_homography,
    heel_taps_allowed,
    line_from_endpoints,
)
from app.media.transcode import extract_frame_bgr
from app.models.schemas import (
    AimOut,
    AimRequest,
    CalibrateRequest,
    CalibrationOut,
    LineSeg,
    OutcomeCreate,
    OutcomeOut,
    Point,
)
from app.serialize import calibration_out

router = APIRouter(tags=["measure"])


def _to_px(p: Point, width: int, height: int) -> np.ndarray:
    return np.array([p.x * width, p.y * height], dtype=float)


def _from_px(xy: np.ndarray, width: int, height: int) -> dict:
    return {"x": float(xy[0] / width), "y": float(xy[1] / height)}


def _line_dict(line, width: int, height: int, role: str) -> dict:
    return {
        "a": _from_px(line.a, width, height),
        "b": _from_px(line.b, width, height),
        "role": role,
    }


@router.post("/api/swings/{swing_id}/calibrate", response_model=CalibrationOut)
async def calibrate(
    swing_id: uuid.UUID,
    body: CalibrateRequest,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> CalibrationOut:
    swing = await require_swing_owner(db, user, swing_id)
    if swing.transcode_status != TranscodeStatus.ready or not swing.storage_path:
        raise HTTPException(status_code=409, detail="Video is not ready.")
    if swing.width is None or swing.height is None or swing.fps is None:
        raise HTTPException(status_code=409, detail="Missing video metrics.")
    width, height = swing.width, swing.height
    path = Path(swing.storage_path)
    frame = await asyncio.to_thread(
        extract_frame_bgr, path, body.frame, swing.fps
    )

    if body.lines:
        fitted = [
            line_from_endpoints(_to_px(seg.a, width, height), _to_px(seg.b, width, height))
            for seg in body.lines
        ]
        line_count = len(fitted)
        try:
            assigned = assign_lines(fitted)
        except LineAssignError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    else:
        fitted = await asyncio.to_thread(detect_stick_lines, frame)
        line_count = len(fitted)
        try:
            assigned = assign_lines(fitted)
        except LineAssignError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    try:
        H, residual = fit_homography(
            assigned.calib, body.stick_length_m, body.stick_separation_m
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    view = CameraView(body.view)
    calib_payload = [_line_dict(ln, width, height, "calib") for ln in assigned.calib]
    toe_payload = (
        _line_dict(assigned.toe, width, height, "toe") if assigned.toe else None
    )

    existing = await db.get(Calibration, swing.id)
    if existing:
        existing.frame = body.frame
        existing.homography = H.tolist()
        existing.stick_length_m = body.stick_length_m
        existing.stick_separation_m = body.stick_separation_m
        existing.residual_px = residual
        existing.view = view
        existing.calib_lines = calib_payload
        existing.toe_line = toe_payload
        row = existing
    else:
        row = Calibration(
            swing_id=swing.id,
            frame=body.frame,
            homography=H.tolist(),
            stick_length_m=body.stick_length_m,
            stick_separation_m=body.stick_separation_m,
            residual_px=residual,
            view=view,
            calib_lines=calib_payload,
            toe_line=toe_payload,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return calibration_out(row, line_count, assigned.message)


@router.post("/api/swings/{swing_id}/aim", response_model=AimOut)
async def measure_aim(
    swing_id: uuid.UUID,
    body: AimRequest,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> AimOut:
    swing = await require_swing_owner(db, user, swing_id)
    calib = await db.get(Calibration, swing.id)
    if calib is None:
        raise HTTPException(status_code=400, detail="Calibrate this swing first.")
    if swing.width is None or swing.height is None:
        raise HTTPException(status_code=409, detail="Missing video metrics.")
    width, height = swing.width, swing.height
    H = np.array(calib.homography, dtype=float)

    method = AimMethod(body.method)
    if method == AimMethod.heel_taps:
        if not heel_taps_allowed(calib.view.value):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Heel taps from down-the-line are not accurate enough to report "
                    "(about 5.5° error). Add a third stick across the toes, or shoot face-on."
                ),
            )
        if body.heel_a is None or body.heel_b is None:
            raise HTTPException(status_code=400, detail="Tap both heels.")
        feet_a = _to_px(body.heel_a, width, height)
        feet_b = _to_px(body.heel_b, width, height)
        toe_payload = None
        heel_a = body.heel_a.model_dump()
        heel_b = body.heel_b.model_dump()
        error_band = settings.heel_error_band_deg
    else:
        toe = body.toe_line or (
            LineSeg.model_validate(calib.toe_line) if calib.toe_line else None
        )
        if toe is None:
            raise HTTPException(
                status_code=400,
                detail="No toe stick. Confirm the detected toe line, or use heel taps face-on.",
            )
        feet_a = _to_px(toe.a, width, height)
        feet_b = _to_px(toe.b, width, height)
        toe_payload = toe.model_dump()
        heel_a = heel_b = None
        error_band = settings.toe_error_band_deg

    target_a = np.array(
        [calib.calib_lines[0]["a"]["x"] * width, calib.calib_lines[0]["a"]["y"] * height]
    )
    target_b = np.array(
        [calib.calib_lines[0]["b"]["x"] * width, calib.calib_lines[0]["b"]["y"] * height]
    )
    angle = feet_angle_deg(H, feet_a, feet_b, target_a, target_b)
    verdict = coarse_verdict(angle)
    use_number = calib.residual_px <= settings.residual_px_number_max
    row = AimMeasurement(
        swing_id=swing.id,
        method=method,
        view=calib.view,
        heel_a=heel_a,
        heel_b=heel_b,
        toe_line=toe_payload,
        feet_angle_deg=angle if use_number else None,
        error_band_deg=error_band if use_number else None,
        verdict=verdict if not use_number else None,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    message = None
    if not use_number:
        message = (
            f"Stick fit residual is {calib.residual_px:.1f} px — too high for a number. "
            f"Coarse reading: {verdict.replace('_', ' ')}."
        )
    return AimOut(
        id=row.id,
        swing_id=row.swing_id,
        method=row.method.value,
        view=row.view.value,
        heel_a=Point(**heel_a) if heel_a else None,
        heel_b=Point(**heel_b) if heel_b else None,
        toe_line=LineSeg.model_validate(toe_payload) if toe_payload else None,
        feet_angle_deg=row.feet_angle_deg,
        error_band_deg=row.error_band_deg,
        verdict=row.verdict,
        message=message,
        created_at=row.created_at,
    )


@router.get("/api/swings/{swing_id}/aim", response_model=AimOut | None)
async def latest_aim(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> AimOut | None:
    await get_swing(db, swing_id)
    result = await db.execute(
        select(AimMeasurement)
        .where(AimMeasurement.swing_id == swing_id)
        .order_by(AimMeasurement.created_at.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return AimOut(
        id=row.id,
        swing_id=row.swing_id,
        method=row.method.value,
        view=row.view.value,
        heel_a=Point(**row.heel_a) if row.heel_a else None,
        heel_b=Point(**row.heel_b) if row.heel_b else None,
        toe_line=LineSeg.model_validate(row.toe_line) if row.toe_line else None,
        feet_angle_deg=row.feet_angle_deg,
        error_band_deg=row.error_band_deg,
        verdict=row.verdict,
        created_at=row.created_at,
    )


@router.get("/api/swings/{swing_id}/calibration", response_model=CalibrationOut | None)
async def get_calibration(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> CalibrationOut | None:
    await get_swing(db, swing_id)
    row = await db.get(Calibration, swing_id)
    if row is None:
        return None
    n = len(row.calib_lines) + (1 if row.toe_line else 0)
    return calibration_out(row, n, None)


@router.post("/api/swings/{swing_id}/outcome", response_model=OutcomeOut)
async def tag_outcome(
    swing_id: uuid.UUID,
    body: OutcomeCreate,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> OutcomeOut:
    await require_swing_owner(db, user, swing_id)
    existing = (
        await db.execute(select(Outcome).where(Outcome.swing_id == swing_id))
    ).scalar_one_or_none()
    if existing:
        existing.result = OutcomeResult(body.result)
        existing.note = body.note
        row = existing
    else:
        row = Outcome(
            swing_id=swing_id,
            result=OutcomeResult(body.result),
            note=body.note,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return OutcomeOut(
        id=row.id,
        swing_id=row.swing_id,
        result=row.result.value,
        note=row.note,
        created_at=row.created_at,
    )


@router.get("/api/swings/{swing_id}/outcome", response_model=OutcomeOut | None)
async def get_outcome(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OutcomeOut | None:
    await get_swing(db, swing_id)
    row = (
        await db.execute(select(Outcome).where(Outcome.swing_id == swing_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    return OutcomeOut(
        id=row.id,
        swing_id=row.swing_id,
        result=row.result.value,
        note=row.note,
        created_at=row.created_at,
    )

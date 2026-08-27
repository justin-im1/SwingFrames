from __future__ import annotations

from pathlib import Path

from app.config import settings
from app.db.models import Annotation, Calibration, Swing
from app.models.schemas import (
    AnnotationOut,
    CalibrationOut,
    LineSeg,
    Point,
    SwingOut,
)


def swing_out(swing: Swing) -> SwingOut:
    ratio = swing.distinct_frame_ratio
    return SwingOut(
        id=swing.id,
        session_id=swing.session_id,
        created_at=swing.created_at,
        label=swing.label,
        filename=swing.filename,
        width=swing.width,
        height=swing.height,
        fps=swing.fps,
        frame_count=swing.frame_count,
        duration_s=swing.duration_s,
        distinct_frame_ratio=ratio,
        transcode_status=swing.transcode_status.value,
        error_message=swing.error_message,
        low_distinct_frames=bool(
            ratio is not None and ratio < settings.distinct_frame_warn_ratio
        ),
    )


def annotation_out(row: Annotation) -> AnnotationOut:
    return AnnotationOut(
        id=row.id,
        swing_id=row.swing_id,
        frame=row.frame,
        kind=row.kind.value,
        points=[Point(x=p["x"], y=p["y"]) for p in row.points],
        style=row.style,
        label=row.label,
        sticky=row.sticky,
        created_at=row.created_at,
    )


def _line_seg(data: dict, role: str | None = None) -> LineSeg:
    return LineSeg(
        a=Point(x=data["a"]["x"], y=data["a"]["y"]),
        b=Point(x=data["b"]["x"], y=data["b"]["y"]),
        role=data.get("role") or role,  # type: ignore[arg-type]
    )


def calibration_out(row: Calibration, line_count: int, message: str | None) -> CalibrationOut:
    return CalibrationOut(
        swing_id=row.swing_id,
        frame=row.frame,
        homography=row.homography,
        stick_length_m=row.stick_length_m,
        stick_separation_m=row.stick_separation_m,
        residual_px=row.residual_px,
        view=row.view.value,
        calib_lines=[_line_seg(x, "calib") for x in row.calib_lines],
        toe_line=_line_seg(row.toe_line, "toe") if row.toe_line else None,
        line_count=line_count,
        message=message,
    )


def media_path(swing: Swing) -> Path | None:
    if not swing.storage_path:
        return None
    path = Path(swing.storage_path)
    if path.exists():
        return path
    return None

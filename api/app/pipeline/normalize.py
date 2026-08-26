"""Scale, canonical yaw, and handedness mirroring."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.pipeline.landmarks import (
    LEAD_WRIST_RH,
    LEFT_ANKLE,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_ANKLE,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
    TRAIL_WRIST_RH,
    VERTICAL_AXIS,
    hip_center,
    hip_line,
    mirror_landmarks,
    shoulder_center,
)
from app.pipeline.signal import smooth_then_diff


@dataclass
class NormalizeResult:
    xyz: np.ndarray
    handedness: str
    scale: float
    yaw_rad: float
    address_idx: int
    quality_flags: list[dict]


def coarse_address_idx(xyz: np.ndarray, timestamps: np.ndarray) -> int:
    """First sustained low-motion window on the mean wrist."""
    n = xyz.shape[0]
    if n < 4:
        return 0
    dt = float(np.median(np.diff(timestamps))) if n > 1 else 1.0 / 240.0
    left = xyz[:, LEFT_WRIST]
    right = xyz[:, RIGHT_WRIST]
    wrist = np.nanmean(np.stack([left, right], axis=0), axis=0)
    speed = np.linalg.norm(
        np.stack([smooth_then_diff(wrist[:, c], dt) for c in range(3)], axis=1),
        axis=1,
    )
    speed = np.where(np.isfinite(speed), speed, np.nan)
    finite = speed[np.isfinite(speed)]
    if finite.size == 0:
        return 0
    thresh = np.nanpercentile(finite, 20)
    window = max(3, int(round(0.25 / dt)))
    below = speed < thresh
    run = 0
    for i, flag in enumerate(below):
        run = run + 1 if flag else 0
        if run >= window:
            return max(0, i - window // 2)
    # Fallback: first 10% of the clip (typical address hold).
    return 0


def _rotation_about_vertical(yaw: float) -> np.ndarray:
    c, s = np.cos(yaw), np.sin(yaw)
    # y is vertical: rotate in the XZ plane.
    r = np.eye(3)
    r[0, 0] = c
    r[0, 2] = s
    r[2, 0] = -s
    r[2, 2] = c
    return r


def _detect_handedness(xyz: np.ndarray, timestamps: np.ndarray) -> str:
    """Lead wrist is typically faster through the downswing (left wrist for RH)."""
    dt = float(np.median(np.diff(timestamps))) if xyz.shape[0] > 1 else 1.0 / 240.0
    peaks = []
    for idx in (LEFT_WRIST, RIGHT_WRIST):
        series = xyz[:, idx]
        speed = np.linalg.norm(
            np.stack([smooth_then_diff(series[:, c], dt) for c in range(3)], axis=1),
            axis=1,
        )
        peaks.append(float(np.nanmax(speed)) if np.isfinite(speed).any() else 0.0)
    # Higher peak speed → lead wrist. Left lead ⇒ right-handed.
    return "right" if peaks[0] >= peaks[1] else "left"


def normalize_landmarks(
    xyz: np.ndarray,
    timestamps: np.ndarray,
    vis: np.ndarray | None = None,
    handedness_hint: str | None = None,
) -> NormalizeResult:
    flags: list[dict] = []
    address = coarse_address_idx(xyz, timestamps)
    addr = xyz[address]

    sw = np.linalg.norm(addr[LEFT_SHOULDER] - addr[RIGHT_SHOULDER])
    hs = np.linalg.norm(shoulder_center(addr) - hip_center(addr))
    scale = sw if np.isfinite(sw) and sw > 1e-4 else hs
    if not np.isfinite(scale) or scale < 1e-4:
        scale = 1.0
        flags.append(
            {
                "code": "scale_fallback",
                "severity": "warning",
                "message": "Could not measure shoulder width at address; skipped scale normalization.",
                "details": {},
            }
        )

    scaled = xyz / scale

    hip = hip_line(scaled[address])
    hip_h = hip.copy()
    hip_h[VERTICAL_AXIS] = 0.0
    yaw = float(np.arctan2(hip_h[2], hip_h[0]))
    rot = _rotation_about_vertical(yaw)
    rotated = scaled @ rot.T

    if handedness_hint in ("left", "right"):
        handedness = handedness_hint
    else:
        handedness = _detect_handedness(rotated, timestamps)

    if handedness == "left":
        rotated = mirror_landmarks(rotated)
        flags.append(
            {
                "code": "mirrored_left_handed",
                "severity": "info",
                "message": "Left-handed swing mirrored so downstream logic assumes right-handed.",
                "details": {},
            }
        )

    return NormalizeResult(
        xyz=rotated,
        handedness=handedness,
        scale=float(scale),
        yaw_rad=yaw,
        address_idx=address,
        quality_flags=flags,
    )


# Re-export lead indices after RH assumption.
LEAD_WRIST = LEAD_WRIST_RH
TRAIL_WRIST = TRAIL_WRIST_RH
LEAD_ANKLE = LEFT_ANKLE
TRAIL_ANKLE = RIGHT_ANKLE

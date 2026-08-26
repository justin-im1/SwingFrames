"""Confidence gating, One Euro filter, resampling to a common time base."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from app.config import settings
from app.pipeline.landmarks import LEFT_ANKLE, RIGHT_ANKLE
from app.pipeline.signal import (
    filter_landmarks,
    mean_frame_jitter,
    resample_landmarks,
    resample_series,
)

VISIBILITY_GATE = 0.5
MISSING_FRACTION_LIMIT = 0.20


@dataclass
class CleanResult:
    timestamps: np.ndarray
    xyz: np.ndarray
    vis: np.ndarray
    image_lm: np.ndarray | None
    jitter_before: float
    jitter_after: float
    jitter_landmark: int
    quality_flags: list[dict]


def _gate(xyz: np.ndarray, vis: np.ndarray, threshold: float = VISIBILITY_GATE) -> np.ndarray:
    out = xyz.copy()
    out[vis < threshold] = np.nan
    return out


def missing_fraction(xyz: np.ndarray, landmark: int, start: int, end: int) -> float:
    window = xyz[start:end, landmark]
    if window.size == 0:
        return 1.0
    missing = np.any(~np.isfinite(window), axis=1)
    return float(np.mean(missing))


def metric_unreliable(
    xyz: np.ndarray, landmark: int, start: int, end: int, limit: float = MISSING_FRACTION_LIMIT
) -> bool:
    return missing_fraction(xyz, landmark, start, end) > limit


def clean_landmarks(
    xyz: np.ndarray,
    vis: np.ndarray,
    fps: float,
    image_lm: np.ndarray | None = None,
    min_cutoff: float = 1.0,
    beta: float = 0.007,
) -> CleanResult:
    n = xyz.shape[0]
    t = np.arange(n, dtype=float) / float(fps)

    gated = _gate(xyz, vis)
    jitter_l = mean_frame_jitter(gated, LEFT_ANKLE)
    jitter_r = mean_frame_jitter(gated, RIGHT_ANKLE)
    if not np.isfinite(jitter_l) and not np.isfinite(jitter_r):
        jitter_landmark = LEFT_ANKLE
        jitter_before = float("nan")
    elif not np.isfinite(jitter_l):
        jitter_landmark = RIGHT_ANKLE
        jitter_before = jitter_r
    elif not np.isfinite(jitter_r):
        jitter_landmark = LEFT_ANKLE
        jitter_before = jitter_l
    else:
        # The more stationary ankle is the better jitter probe.
        if jitter_l <= jitter_r:
            jitter_landmark = LEFT_ANKLE
            jitter_before = jitter_l
        else:
            jitter_landmark = RIGHT_ANKLE
            jitter_before = jitter_r

    filtered = filter_landmarks(gated, t, min_cutoff=min_cutoff, beta=beta)
    jitter_after = mean_frame_jitter(filtered, jitter_landmark)

    duration = t[-1] if n > 1 else 0.0
    hz = settings.resample_hz
    n_new = max(2, int(round(duration * hz)) + 1)
    t_new = np.linspace(0.0, duration, n_new)
    xyz_r, vis_r = resample_landmarks(t, filtered, vis, t_new)
    xyz_r = _gate(xyz_r, vis_r)

    image_r = None
    if image_lm is not None:
        image_r = np.empty((n_new, image_lm.shape[1], image_lm.shape[2]), dtype=float)
        for lm in range(image_lm.shape[1]):
            for c in range(image_lm.shape[2]):
                image_r[:, lm, c] = resample_series(t, image_lm[:, lm, c], t_new)

    flags = [
        {
            "code": "jitter_reduction",
            "severity": "info",
            "message": (
                f"Ankle jitter {jitter_before * 1000:.1f} mm → "
                f"{jitter_after * 1000:.1f} mm after One Euro filter "
                f"(landmark {jitter_landmark})."
                if np.isfinite(jitter_before) and np.isfinite(jitter_after)
                else "Ankle jitter could not be measured (insufficient valid frames)."
            ),
            "details": {
                "before_m": None if not np.isfinite(jitter_before) else jitter_before,
                "after_m": None if not np.isfinite(jitter_after) else jitter_after,
                "landmark": jitter_landmark,
                "resample_hz": hz,
            },
        }
    ]
    return CleanResult(
        timestamps=t_new,
        xyz=xyz_r,
        vis=vis_r,
        image_lm=image_r,
        jitter_before=jitter_before,
        jitter_after=jitter_after,
        jitter_landmark=jitter_landmark,
        quality_flags=flags,
    )

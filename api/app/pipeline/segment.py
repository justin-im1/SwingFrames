"""Swing phase segmentation from lead-wrist motion energy."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from scipy.signal import find_peaks

from app.pipeline.landmarks import LEAD_WRIST_RH, LEFT_WRIST
from app.pipeline.signal import nan_savgol, smooth_then_diff

LEAD_WRIST = LEAD_WRIST_RH


@dataclass
class PhaseResult:
    address_idx: int
    top_idx: int
    impact_idx: int
    finish_idx: int
    confidence: float
    energy: np.ndarray
    wrist_speed: np.ndarray
    quality_flags: list[dict]


def lead_wrist_speed(xyz: np.ndarray, timestamps: np.ndarray, landmark: int = LEFT_WRIST) -> np.ndarray:
    dt = float(np.median(np.diff(timestamps))) if xyz.shape[0] > 1 else 1.0 / 240.0
    pos = xyz[:, landmark]
    vel = np.stack([smooth_then_diff(pos[:, c], dt) for c in range(3)], axis=1)
    return np.linalg.norm(vel, axis=1)


def motion_energy(speed: np.ndarray) -> np.ndarray:
    energy = nan_savgol(speed, window=21)
    return np.where(np.isfinite(energy), energy, 0.0)


def _first_low_window(energy: np.ndarray, dt: float, q: float = 25.0) -> int:
    """End of the first sustained low-motion hold (takeaway / start of backswing)."""
    thresh = np.percentile(energy, q)
    window = max(3, int(round(0.20 / dt)))
    below = energy <= thresh
    run = 0
    for i, flag in enumerate(below):
        run = run + 1 if flag else 0
        if run >= window:
            j = i
            while j + 1 < len(below) and below[j + 1]:
                j += 1
            return j
    return 0


def _top_of_backswing(xyz: np.ndarray, address: int, landmark: int) -> int:
    """Direction reversal: first peak of lead-wrist distance from address."""
    n = xyz.shape[0]
    wrist = xyz[:, landmark]
    addr = wrist[address]
    search_end = min(n, address + max(8, int(0.55 * (n - address))))
    dist = np.linalg.norm(wrist[address:search_end] - addr, axis=1)
    if not np.isfinite(dist).any():
        return min(n - 1, address + 1)
    filled = np.where(np.isfinite(dist), dist, 0.0)
    std = float(np.std(filled))
    prominence = std * 0.15 if std > 0 else None
    peaks, _ = find_peaks(filled, prominence=prominence)
    if peaks.size:
        return min(n - 1, address + int(peaks[0]))
    return min(n - 1, address + int(np.nanargmax(dist)))


def _impact_idx(
    speed: np.ndarray,
    xyz: np.ndarray,
    top: int,
    landmark: int,
) -> tuple[int, str]:
    """Peak lead-wrist speed after the top; fall back to minimum hand height."""
    n = speed.size
    window = speed[top:]
    if window.size < 2:
        return min(n - 1, top + 1), "peak_speed"
    peak_rel = int(np.nanargmax(window))
    peak_val = window[peak_rel]
    if np.isfinite(peak_val) and peak_val > 1e-6:
        return min(n - 1, top + peak_rel), "peak_speed"
    pos = xyz[top:, landmark]
    y = pos[:, 1]
    if np.isfinite(y).sum() >= 2:
        min_rel = int(np.nanargmin(y))
        max_rel = int(np.nanargmax(y))
        cand = min_rel if abs(min_rel - peak_rel) <= abs(max_rel - peak_rel) else max_rel
        return min(n - 1, top + cand), "min_hand_height"
    return min(n - 1, top + peak_rel), "peak_speed"


def _finish_idx(energy: np.ndarray, impact: int, dt: float) -> int:
    n = energy.size
    after = energy[impact:]
    if after.size < 2:
        return n - 1
    thresh = np.percentile(energy, 20)
    window = max(3, int(round(0.20 / dt)))
    below = after <= thresh
    run = 0
    for i, flag in enumerate(below):
        run = run + 1 if flag else 0
        if run >= window:
            return min(n - 1, impact + i - window // 2)
    return n - 1


def segment_swing(
    xyz: np.ndarray,
    timestamps: np.ndarray,
    landmark: int = LEAD_WRIST,
) -> PhaseResult:
    flags: list[dict] = []
    n = xyz.shape[0]
    dt = float(np.median(np.diff(timestamps))) if n > 1 else 1.0 / 240.0
    speed = lead_wrist_speed(xyz, timestamps, landmark=landmark)
    energy = motion_energy(speed)

    address = _first_low_window(energy, dt)
    top = _top_of_backswing(xyz, address, landmark)
    if top <= address:
        top = min(n - 1, address + max(2, int(0.2 / dt)))
        flags.append(
            {
                "code": "top_fallback",
                "severity": "warning",
                "message": "Top of backswing was unclear; used a time-based fallback.",
                "details": {},
            }
        )
    impact, impact_method = _impact_idx(speed, xyz, top, landmark)
    if impact <= top:
        impact = min(n - 1, top + max(2, int(0.15 / dt)))
        flags.append(
            {
                "code": "impact_fallback",
                "severity": "warning",
                "message": "Impact was unclear; used a time-based fallback.",
                "details": {},
            }
        )
    finish = _finish_idx(energy, impact, dt)
    if finish <= impact:
        finish = n - 1

    # Confidence: ordered indices, energy contrast, and non-degenerate durations.
    ordered = address < top < impact < finish
    backswing = timestamps[top] - timestamps[address]
    downswing = timestamps[impact] - timestamps[top]
    duration_ok = 0.15 < backswing < 4.0 and 0.08 < downswing < 1.5
    contrast = float(np.nanmax(energy) / (np.nanpercentile(energy, 20) + 1e-9))
    conf = 0.2
    if ordered:
        conf += 0.35
    if duration_ok:
        conf += 0.25
    if contrast > 4.0:
        conf += 0.2
    conf = float(np.clip(conf, 0.0, 1.0))
    if impact_method == "min_hand_height":
        conf = min(conf, 0.7)
        flags.append(
            {
                "code": "impact_height_fallback",
                "severity": "info",
                "message": "Impact used minimum hand height because wrist-speed peak was flat.",
                "details": {},
            }
        )
    if conf < 0.55:
        flags.append(
            {
                "code": "segmentation_low",
                "severity": "warning",
                "message": (
                    f"Segmentation confidence {conf:.2f} is low; tempo and sequence "
                    "results may be unreliable."
                ),
                "details": {"confidence": conf},
            }
        )

    return PhaseResult(
        address_idx=int(address),
        top_idx=int(top),
        impact_idx=int(impact),
        finish_idx=int(finish),
        confidence=conf,
        energy=energy,
        wrist_speed=speed,
        quality_flags=flags,
    )

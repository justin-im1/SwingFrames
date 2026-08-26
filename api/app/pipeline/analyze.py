"""Tempo ratio and kinematic sequence. Smooth before every derivative."""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from scipy.signal import find_peaks

from app.pipeline.clean import metric_unreliable
from app.pipeline.landmarks import (
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    hip_line,
    shoulder_line,
    transverse_angle,
    unwrap_degrees,
)
from app.pipeline.signal import smooth_then_diff


@dataclass
class AnalyzeResult:
    pelvis_rotation: np.ndarray
    torso_rotation: np.ndarray
    lead_arm_angle: np.ndarray
    pelvis_velocity: np.ndarray
    torso_velocity: np.ndarray
    arm_velocity: np.ndarray
    backswing_duration_s: float | None
    downswing_duration_s: float | None
    tempo_ratio: float | None
    pelvis_peak_time_s: float | None
    torso_peak_time_s: float | None
    arm_peak_time_s: float | None
    sequence_order_correct: bool | None
    pelvis_torso_gap_ms: float | None
    torso_arm_gap_ms: float | None
    peak_magnitude_ratios: dict[str, float] | None
    unreliable_metrics: list[str] = field(default_factory=list)
    quality_flags: list[dict] = field(default_factory=list)


def _lead_arm_angle(xyz: np.ndarray) -> np.ndarray:
    vec = xyz[:, LEFT_WRIST] - xyz[:, LEFT_SHOULDER]
    return unwrap_degrees(transverse_angle(vec))


def _peak_in_window(vel: np.ndarray, start: int, end: int) -> tuple[int | None, float | None]:
    seg = vel[start : end + 1]
    if seg.size < 3 or not np.isfinite(seg).any():
        return None, None
    filled = np.where(np.isfinite(seg), seg, -np.inf)
    std = float(np.nanstd(seg[np.isfinite(seg)]))
    prominence = std * 0.15 if np.isfinite(std) and std > 0 else None
    peaks, _ = find_peaks(filled, prominence=prominence)
    if peaks.size:
        rel = int(peaks[np.argmax(filled[peaks])])
    else:
        rel = int(np.nanargmax(seg))
    mag = float(seg[rel]) if np.isfinite(seg[rel]) else None
    return start + rel, mag


def analyze_swing(
    xyz: np.ndarray,
    timestamps: np.ndarray,
    address_idx: int,
    top_idx: int,
    impact_idx: int,
    finish_idx: int | None = None,
) -> AnalyzeResult:
    flags: list[dict] = []
    unreliable: list[str] = []
    dt = float(np.median(np.diff(timestamps))) if xyz.shape[0] > 1 else 1.0 / 240.0

    pelvis = unwrap_degrees(transverse_angle(hip_line(xyz)))
    torso = unwrap_degrees(transverse_angle(shoulder_line(xyz)))
    arm = _lead_arm_angle(xyz)

    pelvis_v = smooth_then_diff(pelvis, dt)
    torso_v = smooth_then_diff(torso, dt)
    arm_v = smooth_then_diff(arm, dt)

    def flag_unreliable(name: str, message: str) -> None:
        unreliable.append(name)
        flags.append(
            {
                "code": "metric_unreliable",
                "severity": "warning",
                "message": message,
                "details": {"metric": name},
            }
        )

    needed = {
        "pelvis": [LEFT_HIP, RIGHT_HIP],
        "torso": [LEFT_SHOULDER, RIGHT_SHOULDER],
        "arm": [LEFT_SHOULDER, LEFT_WRIST],
    }
    for metric, lms in needed.items():
        for lm in lms:
            if metric_unreliable(xyz, lm, top_idx, impact_idx + 1):
                flag_unreliable(
                    metric,
                    f"{metric} landmarks were gated out for more than 20% of the downswing; "
                    "the number is not reported.",
                )
                break

    backswing = downswing = tempo = None
    if address_idx < top_idx < impact_idx:
        backswing = float(timestamps[top_idx] - timestamps[address_idx])
        downswing = float(timestamps[impact_idx] - timestamps[top_idx])
        if downswing > 1e-6:
            tempo = backswing / downswing
        else:
            flag_unreliable("tempo_ratio", "Downswing duration was ~0; tempo is not reported.")
    else:
        flag_unreliable("tempo_ratio", "Phase indices were not ordered; tempo is not reported.")

    pelvis_peak_t = torso_peak_t = arm_peak_t = None
    pelvis_mag = torso_mag = arm_mag = None
    pt_gap = ta_gap = None
    order = None
    ratios = None

    if "pelvis" not in unreliable:
        p_idx, pelvis_mag = _peak_in_window(pelvis_v, top_idx, impact_idx)
        if p_idx is not None:
            pelvis_peak_t = float(timestamps[p_idx])
        else:
            flag_unreliable("pelvis", "No pelvis velocity peak in the downswing window.")
    if "torso" not in unreliable:
        t_idx, torso_mag = _peak_in_window(torso_v, top_idx, impact_idx)
        if t_idx is not None:
            torso_peak_t = float(timestamps[t_idx])
        else:
            flag_unreliable("torso", "No torso velocity peak in the downswing window.")
    else:
        t_idx = None
    if "arm" not in unreliable:
        a_idx, arm_mag = _peak_in_window(arm_v, top_idx, impact_idx)
        if a_idx is not None:
            arm_peak_t = float(timestamps[a_idx])
        else:
            flag_unreliable("arm", "No arm velocity peak in the downswing window.")
    else:
        a_idx = None

    if pelvis_peak_t is not None and torso_peak_t is not None:
        pt_gap = (torso_peak_t - pelvis_peak_t) * 1000.0
    if torso_peak_t is not None and arm_peak_t is not None:
        ta_gap = (arm_peak_t - torso_peak_t) * 1000.0

    if pelvis_peak_t is not None and torso_peak_t is not None and arm_peak_t is not None:
        order = pelvis_peak_t <= torso_peak_t <= arm_peak_t
        if pelvis_mag and torso_mag and arm_mag and pelvis_mag != 0:
            ratios = {
                "torso_over_pelvis": float(torso_mag / pelvis_mag),
                "arm_over_torso": float(arm_mag / torso_mag) if torso_mag else float("nan"),
                "arm_over_pelvis": float(arm_mag / pelvis_mag),
            }

    return AnalyzeResult(
        pelvis_rotation=pelvis,
        torso_rotation=torso,
        lead_arm_angle=arm,
        pelvis_velocity=pelvis_v,
        torso_velocity=torso_v,
        arm_velocity=arm_v,
        backswing_duration_s=backswing,
        downswing_duration_s=downswing,
        tempo_ratio=tempo,
        pelvis_peak_time_s=pelvis_peak_t,
        torso_peak_time_s=torso_peak_t,
        arm_peak_time_s=arm_peak_t,
        sequence_order_correct=order,
        pelvis_torso_gap_ms=pt_gap,
        torso_arm_gap_ms=ta_gap,
        peak_magnitude_ratios=ratios,
        unreliable_metrics=unreliable,
        quality_flags=flags,
    )


def downsample_skeleton(xyz: np.ndarray, timestamps: np.ndarray, hz: float = 30.0) -> dict:
    n = xyz.shape[0]
    if n == 0:
        return {"timestamps": [], "landmarks": []}
    duration = float(timestamps[-1] - timestamps[0])
    n_new = max(2, int(round(duration * hz)) + 1)
    t_new = np.linspace(timestamps[0], timestamps[-1], n_new)
    lm = []
    for t in t_new:
        i = int(np.clip(np.searchsorted(timestamps, t), 0, n - 1))
        row = xyz[i]
        lm.append([[None if not np.isfinite(v) else float(v) for v in pt] for pt in row])
    return {"timestamps": [float(x) for x in t_new], "landmarks": lm}

from __future__ import annotations

import numpy as np

from app.pipeline.landmarks import hip_line, transverse_angle, unwrap_degrees
from app.pipeline.normalize import normalize_landmarks
from tests.conftest import make_synthetic_swing


def test_canonical_yaw_aligns_hip_line() -> None:
    xyz, vis, _, _ = make_synthetic_swing(yaw=0.4)
    # Address hold only — pelvis has not started rotating.
    xyz, vis = xyz[:24], vis[:24]
    t = np.arange(xyz.shape[0]) / 120.0
    result = normalize_landmarks(xyz, t, vis=vis, handedness_hint="right")
    hip = hip_line(result.xyz[0])
    angle = float(transverse_angle(hip))
    assert min(abs(angle), abs(abs(angle) - 180)) < 15.0


def test_yaw_invariance_of_pelvis_series() -> None:
    a, _, _, _ = make_synthetic_swing(yaw=0.0)
    b, _, _, _ = make_synthetic_swing(yaw=0.25)
    t = np.arange(a.shape[0]) / 120.0
    na = normalize_landmarks(a, t, handedness_hint="right")
    nb = normalize_landmarks(b, t, handedness_hint="right")
    ang_a = unwrap_degrees(transverse_angle(hip_line(na.xyz)))
    ang_b = unwrap_degrees(transverse_angle(hip_line(nb.xyz)))
    # Same motion, different capture yaw → similar angles after canonicalize.
    n = min(ang_a.size, ang_b.size)
    err = np.nanmean(np.abs(ang_a[:n] - ang_b[:n]))
    assert err < 8.0


def test_left_handed_mirror_sets_flag() -> None:
    xyz, vis, _, _ = make_synthetic_swing()
    t = np.arange(xyz.shape[0]) / 120.0
    result = normalize_landmarks(xyz, t, vis=vis, handedness_hint="left")
    assert result.handedness == "left"
    assert any(f["code"] == "mirrored_left_handed" for f in result.quality_flags)

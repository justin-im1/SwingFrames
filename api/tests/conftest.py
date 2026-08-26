from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.pipeline.landmarks import (
    LEFT_ANKLE,
    LEFT_HIP,
    LEFT_SHOULDER,
    LEFT_WRIST,
    N_LANDMARKS,
    RIGHT_ANKLE,
    RIGHT_HIP,
    RIGHT_SHOULDER,
    RIGHT_WRIST,
)


def _blank_pose(n: int) -> np.ndarray:
    xyz = np.zeros((n, N_LANDMARKS, 3), dtype=float)
    # Hip-centered T-pose-ish skeleton in meters.
    xyz[:, LEFT_HIP] = [-0.15, 0.0, 0.0]
    xyz[:, RIGHT_HIP] = [0.15, 0.0, 0.0]
    xyz[:, LEFT_SHOULDER] = [-0.20, -0.50, 0.0]
    xyz[:, RIGHT_SHOULDER] = [0.20, -0.50, 0.0]
    xyz[:, LEFT_WRIST] = [-0.45, -0.50, 0.0]
    xyz[:, RIGHT_WRIST] = [0.45, -0.50, 0.0]
    xyz[:, LEFT_ANKLE] = [-0.15, 0.80, 0.0]
    xyz[:, RIGHT_ANKLE] = [0.15, 0.80, 0.0]
    return xyz


@pytest.fixture
def still_pose() -> np.ndarray:
    return _blank_pose(120)


def make_synthetic_swing(
    fps: float = 120.0,
    backswing_s: float = 0.75,
    downswing_s: float = 0.25,
    address_s: float = 0.40,
    finish_s: float = 0.40,
    yaw: float = 0.0,
    face_on: bool = True,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, int]]:
    """Build a kinematic-looking 3D skeleton + 2D image landmarks.

    Wrist traces a rise-then-fall energy profile with known phase times.
    Pelvis/torso/arm rotation peaks are staggered in the downswing.
    """
    t_addr_end = address_s
    t_top = address_s + backswing_s
    t_impact = t_top + downswing_s
    t_end = t_impact + finish_s
    n = int(round(t_end * fps))
    t = np.arange(n) / fps
    xyz = _blank_pose(n)

    def phase_u(t0, t1):
        u = (t - t0) / max(t1 - t0, 1e-6)
        return np.clip(u, 0.0, 1.0)

    u_bs = phase_u(t_addr_end, t_top)
    u_ds = phase_u(t_top, t_impact)
    u_fin = phase_u(t_impact, t_end)
    # Downswing eases in so wrist speed peaks at impact (u^2 → vel ∝ u).
    u_ds_ease = u_ds**2

    xyz[:, LEFT_WRIST, 0] = -0.45 - 0.25 * u_bs + 0.55 * u_ds_ease + 0.05 * u_fin
    xyz[:, LEFT_WRIST, 1] = -0.50 - 0.55 * u_bs + 0.80 * u_ds_ease + 0.05 * u_fin
    xyz[:, LEFT_WRIST, 2] = 0.08 * u_bs - 0.20 * u_ds_ease

    # Trail wrist milder.
    xyz[:, RIGHT_WRIST, 0] = 0.45 + 0.10 * u_bs - 0.05 * u_ds
    xyz[:, RIGHT_WRIST, 1] = -0.50 - 0.20 * u_bs + 0.15 * u_ds

    # Transverse rotations: pelvis then torso then arm, peaking in downswing.
    def bump_angle(t0: float, duration: float, amp_deg: float) -> np.ndarray:
        u = np.clip((t - t0) / max(duration, 1e-6), 0.0, 1.0)
        return np.deg2rad(amp_deg * 0.5 * (1.0 - np.cos(np.pi * u)))

    pelvis_ang = bump_angle(t_top, downswing_s * 0.65, 40.0)
    torso_ang = bump_angle(t_top + 0.06, downswing_s * 0.65, 70.0)
    # Apply as yaw of hip/shoulder lines about vertical (y).
    for i in range(n):
        c, s = np.cos(pelvis_ang[i]), np.sin(pelvis_ang[i])
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        for lm in (LEFT_HIP, RIGHT_HIP, LEFT_ANKLE, RIGHT_ANKLE):
            xyz[i, lm] = r @ xyz[i, lm]
        c, s = np.cos(torso_ang[i]), np.sin(torso_ang[i])
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        for lm in (LEFT_SHOULDER, RIGHT_SHOULDER):
            xyz[i, lm] = r @ xyz[i, lm]

    if yaw != 0.0:
        c, s = np.cos(yaw), np.sin(yaw)
        r = np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
        xyz = xyz @ r.T

    vis = np.ones((n, N_LANDMARKS), dtype=float)

    # 2D image landmarks: project X (horizontal) and Y (vertical) after optional
    # foreshortening of X for down-the-line.
    image = np.zeros_like(xyz)
    scale_x = 1.0 if face_on else 0.18
    # Normalize into [0,1] image coords around center.
    xs = xyz[:, :, 0] * scale_x
    ys = xyz[:, :, 1]
    image[:, :, 0] = 0.5 + xs * 0.6
    image[:, :, 1] = 0.45 + ys * 0.4
    image[:, :, 2] = 0.0

    labels = {
        "address_idx": int(round(t_addr_end * fps)),
        "top_idx": int(round(t_top * fps)),
        "impact_idx": int(round(t_impact * fps)),
        "finish_idx": n - 1,
    }
    return xyz, vis, image, labels

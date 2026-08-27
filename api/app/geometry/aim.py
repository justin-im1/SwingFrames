from __future__ import annotations

import math

import numpy as np

from app.geometry.homography import to_ground


def _wrap_pi(angle: float) -> float:
    while angle > math.pi:
        angle -= 2 * math.pi
    while angle < -math.pi:
        angle += 2 * math.pi
    return angle


def feet_angle_deg(
    H: np.ndarray,
    feet_a: np.ndarray,
    feet_b: np.ndarray,
    target_a: np.ndarray,
    target_b: np.ndarray,
) -> float:
    """Signed angle of the feet line vs the target (calibration) line.

    Ground frame: +x right, +y away from camera.
    Positive degrees = feet aimed right of target; negative = left.
    """
    fa = to_ground(H, np.asarray(feet_a, dtype=float))
    fb = to_ground(H, np.asarray(feet_b, dtype=float))
    ta = to_ground(H, np.asarray(target_a, dtype=float))
    tb = to_ground(H, np.asarray(target_b, dtype=float))
    feet = fb - fa
    target = tb - ta
    heading_target = math.atan2(target[1], target[0])
    heading_feet = math.atan2(feet[1], feet[0])
    diff = _wrap_pi(heading_feet - heading_target)
    # Lines are undirected; pick the representative within ±90°.
    if diff > math.pi / 2:
        diff -= math.pi
    if diff < -math.pi / 2:
        diff += math.pi
    # atan2 CCW from target toward +x is negative heading change from +y.
    # We want +right, which is clockwise from +y toward +x, i.e. -CCW.
    return float(-math.degrees(diff))


def coarse_verdict(angle_deg: float, dead_zone: float = 2.0) -> str:
    if angle_deg > dead_zone:
        return "aimed_right"
    if angle_deg < -dead_zone:
        return "aimed_left"
    return "square"


def heel_taps_allowed(view: str) -> bool:
    return view == "face_on"

"""MediaPipe Pose landmark indices and geometric helpers."""

from __future__ import annotations

import numpy as np

NOSE = 0
LEFT_EYE_INNER = 1
LEFT_EYE = 2
LEFT_EYE_OUTER = 3
RIGHT_EYE_INNER = 4
RIGHT_EYE = 5
RIGHT_EYE_OUTER = 6
LEFT_EAR = 7
RIGHT_EAR = 8
MOUTH_LEFT = 9
MOUTH_RIGHT = 10
LEFT_SHOULDER = 11
RIGHT_SHOULDER = 12
LEFT_ELBOW = 13
RIGHT_ELBOW = 14
LEFT_WRIST = 15
RIGHT_WRIST = 16
LEFT_PINKY = 17
RIGHT_PINKY = 18
LEFT_INDEX = 19
RIGHT_INDEX = 20
LEFT_THUMB = 21
RIGHT_THUMB = 22
LEFT_HIP = 23
RIGHT_HIP = 24
LEFT_KNEE = 25
RIGHT_KNEE = 26
LEFT_ANKLE = 27
RIGHT_ANKLE = 28
LEFT_HEEL = 29
RIGHT_HEEL = 30
LEFT_FOOT_INDEX = 31
RIGHT_FOOT_INDEX = 32

N_LANDMARKS = 33
VERTICAL_AXIS = 1  # MediaPipe world: y is the gravity axis

# Left/right pairs for mirroring left-handed swings.
LR_PAIRS: list[tuple[int, int]] = [
    (LEFT_EYE_INNER, RIGHT_EYE_INNER),
    (LEFT_EYE, RIGHT_EYE),
    (LEFT_EYE_OUTER, RIGHT_EYE_OUTER),
    (LEFT_EAR, RIGHT_EAR),
    (MOUTH_LEFT, MOUTH_RIGHT),
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_ELBOW, RIGHT_ELBOW),
    (LEFT_WRIST, RIGHT_WRIST),
    (LEFT_PINKY, RIGHT_PINKY),
    (LEFT_INDEX, RIGHT_INDEX),
    (LEFT_THUMB, RIGHT_THUMB),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_KNEE, RIGHT_KNEE),
    (LEFT_ANKLE, RIGHT_ANKLE),
    (LEFT_HEEL, RIGHT_HEEL),
    (LEFT_FOOT_INDEX, RIGHT_FOOT_INDEX),
]

# Right-handed lead side is the left side of the body.
LEAD_WRIST_RH = LEFT_WRIST
TRAIL_WRIST_RH = RIGHT_WRIST
LEAD_ANKLE_RH = LEFT_ANKLE
TRAIL_ANKLE_RH = RIGHT_ANKLE
LEAD_SHOULDER_RH = LEFT_SHOULDER
LEAD_HIP_RH = LEFT_HIP

SKELETON_EDGES = [
    (LEFT_SHOULDER, RIGHT_SHOULDER),
    (LEFT_SHOULDER, LEFT_ELBOW),
    (LEFT_ELBOW, LEFT_WRIST),
    (RIGHT_SHOULDER, RIGHT_ELBOW),
    (RIGHT_ELBOW, RIGHT_WRIST),
    (LEFT_SHOULDER, LEFT_HIP),
    (RIGHT_SHOULDER, RIGHT_HIP),
    (LEFT_HIP, RIGHT_HIP),
    (LEFT_HIP, LEFT_KNEE),
    (LEFT_KNEE, LEFT_ANKLE),
    (RIGHT_HIP, RIGHT_KNEE),
    (RIGHT_KNEE, RIGHT_ANKLE),
    (NOSE, LEFT_SHOULDER),
    (NOSE, RIGHT_SHOULDER),
]


def hip_center(xyz: np.ndarray) -> np.ndarray:
    """xyz: (..., 33, 3) → (..., 3)."""
    return 0.5 * (xyz[..., LEFT_HIP, :] + xyz[..., RIGHT_HIP, :])


def shoulder_center(xyz: np.ndarray) -> np.ndarray:
    return 0.5 * (xyz[..., LEFT_SHOULDER, :] + xyz[..., RIGHT_SHOULDER, :])


def hip_line(xyz: np.ndarray) -> np.ndarray:
    """Vector from right hip to left hip."""
    return xyz[..., LEFT_HIP, :] - xyz[..., RIGHT_HIP, :]


def shoulder_line(xyz: np.ndarray) -> np.ndarray:
    return xyz[..., LEFT_SHOULDER, :] - xyz[..., RIGHT_SHOULDER, :]


def project_horizontal(vec: np.ndarray) -> np.ndarray:
    """Zero the vertical component (yaw-relevant plane)."""
    out = np.array(vec, dtype=float, copy=True)
    out[..., VERTICAL_AXIS] = 0.0
    return out


def transverse_angle(line: np.ndarray) -> np.ndarray:
    """Angle of a 3D line in the horizontal plane, degrees.

    World y is vertical, so the ground plane is XZ.
    """
    x = line[..., 0]
    z = line[..., 2]
    return np.degrees(np.arctan2(z, x))


def unwrap_degrees(angles: np.ndarray) -> np.ndarray:
    rad = np.deg2rad(angles)
    unwrapped = np.unwrap(np.where(np.isfinite(rad), rad, 0.0))
    unwrapped = np.where(np.isfinite(angles), unwrapped, np.nan)
    return np.rad2deg(unwrapped)


def mirror_landmarks(xyz: np.ndarray) -> np.ndarray:
    """Mirror across the sagittal plane (negate X) and swap left/right."""
    out = np.array(xyz, dtype=float, copy=True)
    out[..., 0] *= -1.0
    for a, b in LR_PAIRS:
        tmp = out[..., a, :].copy()
        out[..., a, :] = out[..., b, :]
        out[..., b, :] = tmp
    return out


def nan_to_none(values) -> list:
    out = []
    for v in values:
        if v is None or (isinstance(v, float) and not np.isfinite(v)):
            out.append(None)
        else:
            out.append(float(v))
    return out


def nested_nan_to_none(arr: np.ndarray) -> list:
    result = []
    for row in arr:
        result.append(nan_to_none(row))
    return result

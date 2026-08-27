from __future__ import annotations

import numpy as np
import cv2

from app.geometry.detect import FittedLine


def _order_calib_pair(lines: list[FittedLine]) -> tuple[FittedLine, FittedLine]:
    left, right = lines[0], lines[1]
    if left.a[0] > right.a[0]:
        left, right = right, left
    return left, right


def correspondences(
    calib: list[FittedLine], length_m: float, separation_m: float
) -> tuple[np.ndarray, np.ndarray]:
    left, right = _order_calib_pair(calib)
    im = np.vstack([left.samples, right.samples]).astype(np.float32)
    n = len(left.samples)
    t = np.linspace(0.0, 1.0, n)
    # Ground: x right, y away from camera. Near end of each stick is y=0.
    gm_left = np.stack([np.zeros(n), t * length_m], axis=1)
    gm_right = np.stack([np.full(n, separation_m), t * length_m], axis=1)
    gm = np.vstack([gm_left, gm_right]).astype(np.float32)
    return im, gm


def fit_homography(
    calib: list[FittedLine], length_m: float, separation_m: float
) -> tuple[np.ndarray, float]:
    if len(calib) != 2:
        raise ValueError("Homography needs exactly two calibration lines.")
    im, gm = correspondences(calib, length_m, separation_m)
    H, _ = cv2.findHomography(im, gm, 0)
    if H is None:
        raise ValueError("Homography fit failed.")
    residual = reprojection_error_px(H, im, gm)
    return H, residual


def reprojection_error_px(H: np.ndarray, im: np.ndarray, gm: np.ndarray) -> float:
    Hinv = np.linalg.inv(H)
    ones = np.ones((len(gm), 1), dtype=np.float64)
    homog = np.hstack([gm.astype(np.float64), ones])
    pred = (Hinv @ homog.T).T
    pred = pred[:, :2] / pred[:, 2:3]
    err = np.linalg.norm(pred - im.astype(np.float64), axis=1)
    return float(np.mean(err))


def to_ground(H: np.ndarray, pt: np.ndarray) -> np.ndarray:
    q = H @ np.array([pt[0], pt[1], 1.0], dtype=np.float64)
    return q[:2] / q[2]

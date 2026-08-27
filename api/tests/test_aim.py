from __future__ import annotations

import numpy as np

from app.geometry.aim import coarse_verdict, feet_angle_deg, heel_taps_allowed


def _h_image_to_ground() -> np.ndarray:
    """x_g = x_i/100, y_g = 4 - y_i/100. Image y down, ground y away."""
    return np.array(
        [
            [0.01, 0.0, 0.0],
            [0.0, -0.01, 4.0],
            [0.0, 0.0, 1.0],
        ],
        dtype=float,
    )


def _img(xg: float, yg: float) -> np.ndarray:
    return np.array([100.0 * xg, 400.0 - 100.0 * yg])


def test_square_aim_is_zero() -> None:
    H = _h_image_to_ground()
    angle = feet_angle_deg(
        H, _img(0.5, 0.2), _img(0.5, 1.8), _img(1.0, 0.0), _img(1.0, 2.0)
    )
    assert abs(angle) < 0.05


def test_right_positive_left_negative() -> None:
    H = _h_image_to_ground()
    target_a, target_b = _img(1.0, 0.0), _img(1.0, 2.0)
    rad = np.deg2rad(10)
    right = feet_angle_deg(
        H,
        _img(1.0, 0.5),
        _img(1.0 + np.sin(rad), 0.5 + np.cos(rad)),
        target_a,
        target_b,
    )
    left = feet_angle_deg(
        H,
        _img(1.0, 0.5),
        _img(1.0 - np.sin(rad), 0.5 + np.cos(rad)),
        target_a,
        target_b,
    )
    assert 9.5 < right < 10.5
    assert -10.5 < left < -9.5


def test_flipped_feet_vector_same_sign() -> None:
    H = _h_image_to_ground()
    target_a, target_b = _img(1.0, 0.0), _img(1.0, 2.0)
    rad = np.deg2rad(8)
    a = _img(1.0, 0.5)
    b = _img(1.0 + np.sin(rad), 0.5 + np.cos(rad))
    assert abs(
        feet_angle_deg(H, a, b, target_a, target_b)
        - feet_angle_deg(H, b, a, target_a, target_b)
    ) < 0.2


def test_coarse_verdict() -> None:
    assert coarse_verdict(0.4) == "square"
    assert coarse_verdict(3.0) == "aimed_right"
    assert coarse_verdict(-3.0) == "aimed_left"


def test_heel_taps_face_on_only() -> None:
    assert heel_taps_allowed("face_on") is True
    assert heel_taps_allowed("down_the_line") is False

from __future__ import annotations

import numpy as np

from app.geometry.detect import detect_stick_lines, line_from_endpoints
from app.geometry.homography import fit_homography, to_ground


def test_line_from_endpoints_near_is_higher_y() -> None:
    ln = line_from_endpoints(np.array([10.0, 20.0]), np.array([12.0, 200.0]))
    assert ln.a[1] > ln.b[1]


def test_homography_maps_near_end_to_origin_y() -> None:
    left = line_from_endpoints(np.array([100.0, 400.0]), np.array([100.0, 40.0]))
    right = line_from_endpoints(np.array([220.0, 400.0]), np.array([220.0, 40.0]))
    H, residual = fit_homography([left, right], length_m=1.2, separation_m=0.4)
    assert residual < 1.0
    near = to_ground(H, np.array([100.0, 400.0]))
    far = to_ground(H, np.array([100.0, 40.0]))
    assert abs(near[1]) < 0.05
    assert far[1] > near[1]

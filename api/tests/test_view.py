from __future__ import annotations

import numpy as np

from app.pipeline.landmarks import (
    LEFT_HIP,
    LEFT_SHOULDER,
    N_LANDMARKS,
    RIGHT_HIP,
    RIGHT_SHOULDER,
)
from app.pipeline.view import classify_view
from tests.conftest import make_synthetic_swing


def test_face_on_from_wide_shoulders() -> None:
    xyz, vis, image, labels = make_synthetic_swing(face_on=True)
    result = classify_view(image, labels["address_idx"])
    assert result.view_class == "face_on"
    assert result.confidence >= 0.45


def test_down_the_line_from_foreshortened_shoulders() -> None:
    xyz, vis, image, labels = make_synthetic_swing(face_on=False)
    result = classify_view(image, labels["address_idx"])
    assert result.view_class == "down_the_line"
    assert result.confidence >= 0.45


def test_ambiguous_ratio_is_unknown() -> None:
    image = np.zeros((5, N_LANDMARKS, 3))
    # shoulder_sep=0.22, torso_h=0.40 → ratio=0.55, inside the dead band.
    image[:, LEFT_SHOULDER, :2] = [0.39, 0.30]
    image[:, RIGHT_SHOULDER, :2] = [0.61, 0.30]
    image[:, LEFT_HIP, :2] = [0.42, 0.70]
    image[:, RIGHT_HIP, :2] = [0.58, 0.70]
    result = classify_view(image, 0)
    assert result.view_class == "unknown"

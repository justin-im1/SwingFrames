from __future__ import annotations

import numpy as np

from app.pipeline.clean import clean_landmarks
from app.pipeline.landmarks import LEFT_ANKLE, N_LANDMARKS, RIGHT_ANKLE


def test_one_euro_reduces_stationary_jitter() -> None:
    n = 240
    fps = 120.0
    xyz = np.zeros((n, N_LANDMARKS, 3))
    rng = np.random.default_rng(0)
    xyz[:, LEFT_ANKLE] = rng.normal(0.0, 0.012, size=(n, 3))
    xyz[:, RIGHT_ANKLE] = rng.normal(0.0, 0.012, size=(n, 3))
    vis = np.ones((n, N_LANDMARKS))
    result = clean_landmarks(xyz, vis, fps)
    assert result.jitter_after < result.jitter_before * 0.7
    assert any(f["code"] == "jitter_reduction" for f in result.quality_flags)


def test_resample_length_matches_240hz() -> None:
    n = 120
    fps = 60.0
    xyz = np.zeros((n, N_LANDMARKS, 3))
    vis = np.ones((n, N_LANDMARKS))
    result = clean_landmarks(xyz, vis, fps)
    duration = (n - 1) / fps
    expected = int(round(duration * 240.0)) + 1
    assert result.timestamps.shape[0] == expected
    assert result.xyz.shape[0] == expected


def test_low_visibility_is_gated_to_nan() -> None:
    n = 60
    fps = 120.0
    xyz = np.ones((n, N_LANDMARKS, 3))
    vis = np.ones((n, N_LANDMARKS))
    vis[:, LEFT_ANKLE] = 0.1
    result = clean_landmarks(xyz, vis, fps)
    assert np.isnan(result.xyz[:, LEFT_ANKLE]).all()

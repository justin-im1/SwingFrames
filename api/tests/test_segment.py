from __future__ import annotations

import numpy as np

from app.pipeline.normalize import normalize_landmarks
from app.pipeline.segment import segment_swing
from tests.conftest import make_synthetic_swing


def test_phases_near_labelled_synthetic() -> None:
    xyz, vis, _, labels = make_synthetic_swing(fps=120.0)
    t = np.arange(xyz.shape[0]) / 120.0
    norm = normalize_landmarks(xyz, t, vis=vis)
    phases = segment_swing(norm.xyz, t)
    # Allow a generous window: segmentation is energy-based, labels are kinematic.
    fps = 120.0
    assert abs(phases.address_idx - labels["address_idx"]) < 0.35 * fps
    assert abs(phases.top_idx - labels["top_idx"]) < 0.30 * fps
    assert abs(phases.impact_idx - labels["impact_idx"]) < 0.25 * fps
    assert phases.address_idx < phases.top_idx < phases.impact_idx <= phases.finish_idx
    assert phases.confidence > 0.4

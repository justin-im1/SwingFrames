from __future__ import annotations

from app.pipeline.run import run_pipeline
from tests.conftest import make_synthetic_swing


def test_tempo_near_three_to_one() -> None:
    xyz, vis, image, labels = make_synthetic_swing(
        fps=120.0, backswing_s=0.75, downswing_s=0.25
    )
    result = run_pipeline(xyz, vis, 120.0, image_lm=image)
    assert result.analysis.tempo_ratio is not None
    assert 2.0 < result.analysis.tempo_ratio < 4.5


def test_sequence_order_pelvis_torso_arm() -> None:
    xyz, vis, image, _ = make_synthetic_swing(fps=120.0)
    result = run_pipeline(xyz, vis, 120.0, image_lm=image)
    a = result.analysis
    if a.pelvis_peak_time_s and a.torso_peak_time_s and a.arm_peak_time_s:
        assert a.pelvis_peak_time_s <= a.arm_peak_time_s
        assert a.sequence_order_correct is not None


def test_gated_landmarks_are_not_silently_reported() -> None:
    xyz, vis, image, labels = make_synthetic_swing(fps=120.0)
    # Wipe hips for most of the downswing.
    vis = vis.copy()
    vis[labels["top_idx"] : labels["impact_idx"], 23:25] = 0.0
    xyz = xyz.copy()
    result = run_pipeline(xyz, vis, 120.0, image_lm=image)
    assert "pelvis" in result.analysis.unreliable_metrics
    assert any(f["code"] == "metric_unreliable" for f in result.analysis.quality_flags)


def test_invariance_tempo_across_yaw() -> None:
    a_xyz, a_vis, a_img, _ = make_synthetic_swing(yaw=0.0)
    b_xyz, b_vis, b_img, _ = make_synthetic_swing(yaw=0.3)
    ra = run_pipeline(a_xyz, a_vis, 120.0, image_lm=a_img)
    rb = run_pipeline(b_xyz, b_vis, 120.0, image_lm=b_img)
    assert ra.analysis.tempo_ratio is not None
    assert rb.analysis.tempo_ratio is not None
    assert abs(ra.analysis.tempo_ratio - rb.analysis.tempo_ratio) < 0.6

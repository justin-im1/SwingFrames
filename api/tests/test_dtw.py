from __future__ import annotations

import numpy as np
import pytest

from app.pipeline.dtw import deviation_curve, dtw, map_index, phase_duration_ratios


def _ramp(n: int, channels: int = 3) -> np.ndarray:
    x = np.linspace(0.0, 1.0, n)
    return np.stack([x + 0.01 * c for c in range(channels)], axis=1)


def test_identical_series_zero_distance_diagonal() -> None:
    a = _ramp(40)
    result = dtw(a, a.copy())
    assert result.distance == pytest.approx(0.0, abs=1e-6)
    for i, j in result.path:
        assert i == j


def test_time_stretched_copy_path_shows_stretch() -> None:
    short = _ramp(40)
    t = np.linspace(0, 1, 40)
    t2 = np.linspace(0, 1, 80)
    long = np.stack(
        [np.interp(t2, t, short[:, c]) for c in range(short.shape[1])], axis=1
    )
    result = dtw(short, long)
    ratios = [j / max(i, 1) for i, j in result.path if i > 5]
    assert np.median(ratios) == pytest.approx(2.0, rel=0.25)


def test_phase_duration_ratios_recover_stretch_not_mean_deviation() -> None:
    """70+30 vs 30+30: duration ratio recovers ~2.33x on the first half.

    Mean deviation over each half is accumulated lag and must not be used
    as a per-phase timing score (the 0.098 vs 0.099 trap).
    """

    def series(n_first: int, n_second: int) -> np.ndarray:
        first = np.linspace(0.0, 1.0, n_first)
        second = np.linspace(1.0, 0.0, n_second)
        sig = np.concatenate([first, second])
        return np.stack([sig, sig * 0.8, sig * 1.1], axis=1)

    a = series(70, 30)
    b = series(30, 30)
    result = dtw(a, b)
    ts_a = np.arange(100, dtype=float)
    ts_b = np.arange(60, dtype=float)
    ratios = phase_duration_ratios(
        ts_a,
        ts_b,
        result.path,
        {
            "address_idx": 0,
            "top_idx": 70,
            "impact_idx": 99,
            "finish_idx": 99,
        },
    )
    back = next(r for r in ratios if r["name"] == "backswing")
    assert back["swing_a_s"] / back["swing_b_s"] == pytest.approx(70 / 30, rel=0.25)

    curve = deviation_curve(result.path, 100, 60)
    first = [p["deviation"] for p in curve if p["i"] < 70]
    second = [p["deviation"] for p in curve if p["i"] >= 70]
    # Trap exists: half-means can be close while duration ratios are not.
    # We only assert duration ratios; mean deviation is intentionally unused.
    assert first and second


def test_map_index_uses_midpoint_of_one_to_many() -> None:
    path = [(5, 10), (5, 11), (5, 12), (5, 13), (6, 14)]
    assert map_index(path, 5) == 12


def test_sakoe_chiba_allows_length_mismatch() -> None:
    a = _ramp(20)
    b = _ramp(50)
    result = dtw(a, b)
    assert result.path[0] == (0, 0)
    assert result.path[-1] == (19, 49)

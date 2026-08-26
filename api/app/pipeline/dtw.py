"""Multivariate DTW from scratch. No dtaidistance, no fastdtw."""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass
class DTWResult:
    distance: float
    normalized_distance: float
    path: list[tuple[int, int]]
    cost: np.ndarray


def _pooled_scale(a: np.ndarray, b: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Scale channels by std pooled across both series. Do not z-norm independently."""
    pooled = np.concatenate([a, b], axis=0)
    std = np.nanstd(pooled, axis=0)
    std = np.where(~np.isfinite(std) | (std < 1e-8), 1.0, std)
    return a / std, b / std


def dtw(
    a: np.ndarray,
    b: np.ndarray,
    band_frac: float = 0.10,
) -> DTWResult:
    """Symmetric1 DTW with a Sakoe-Chiba band.

    Parameters
    ----------
    a, b : (T, C)
        Multivariate series. Channels are balanced with pooled statistics.
    band_frac :
        Band width as a fraction of the longer series. Width is floored at
        |n - m| so a valid path always exists.
    """
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a.ndim == 1:
        a = a[:, None]
    if b.ndim == 1:
        b = b[:, None]
    a_s, b_s = _pooled_scale(a, b)
    n, m = a_s.shape[0], b_s.shape[0]
    if n == 0 or m == 0:
        raise ValueError("DTW requires non-empty series.")

    band = max(int(np.ceil(band_frac * max(n, m))), abs(n - m))
    inf = 1e30
    dtw_m = np.full((n + 1, m + 1), inf, dtype=float)
    dtw_m[0, 0] = 0.0

    for i in range(1, n + 1):
        j_start = max(1, i - band)
        j_end = min(m, i + band)
        ai = a_s[i - 1]
        for j in range(j_start, j_end + 1):
            bj = b_s[j - 1]
            diff = ai - bj
            # Euclidean local cost; treat NaN coords as 0 contribution after scale.
            diff = np.where(np.isfinite(diff), diff, 0.0)
            cost = float(np.sqrt(np.dot(diff, diff)))
            dtw_m[i, j] = cost + min(
                dtw_m[i - 1, j],
                dtw_m[i, j - 1],
                dtw_m[i - 1, j - 1],
            )

    distance = float(dtw_m[n, m])
    if not np.isfinite(distance) or distance >= inf / 10:
        raise ValueError("DTW found no valid path inside the Sakoe-Chiba band.")

    path: list[tuple[int, int]] = []
    i, j = n, m
    while i > 0 and j > 0:
        path.append((i - 1, j - 1))
        candidates = (
            (dtw_m[i - 1, j - 1], i - 1, j - 1),
            (dtw_m[i - 1, j], i - 1, j),
            (dtw_m[i, j - 1], i, j - 1),
        )
        _, i, j = min(candidates, key=lambda t: t[0])
    path.reverse()

    return DTWResult(
        distance=distance,
        normalized_distance=distance / max(len(path), 1),
        path=path,
        cost=dtw_m[1:, 1:].copy(),
    )


def deviation_curve(path: list[tuple[int, int]], n: int, m: int) -> list[dict[str, float]]:
    """Charting output: j/m - i/n along the path. Do not average this over a phase."""
    n = max(n, 1)
    m = max(m, 1)
    return [
        {
            "i": float(i),
            "j": float(j),
            "i_rel": i / n,
            "j_rel": j / m,
            "deviation": j / m - i / n,
        }
        for i, j in path
    ]


def map_index(path: list[tuple[int, int]], i_query: int) -> int:
    """Map a frame of A onto B. One-to-many: take the midpoint of the matched range."""
    js = [j for i, j in path if i == i_query]
    if js:
        return int(round(0.5 * (js[0] + js[-1])))
    # Nearest path node by i.
    nearest = min(path, key=lambda p: abs(p[0] - i_query))
    js = [j for i, j in path if i == nearest[0]]
    return int(round(0.5 * (js[0] + js[-1])))


def phase_duration_ratios(
    timestamps_a: np.ndarray,
    timestamps_b: np.ndarray,
    path: list[tuple[int, int]],
    phases_a: dict[str, int],
) -> list[dict]:
    """Coaching output: map A's phase boundaries onto B and compare durations.

    Never average the deviation curve over a phase — deviation is accumulated
    lag and can be identical for a slow phase and a fast one.
    """
    names = [
        ("backswing", "address_idx", "top_idx"),
        ("downswing", "top_idx", "impact_idx"),
        ("follow_through", "impact_idx", "finish_idx"),
    ]
    out = []
    for name, start_key, end_key in names:
        sa = phases_a.get(start_key)
        ea = phases_a.get(end_key)
        if sa is None or ea is None:
            out.append(
                {
                    "name": name,
                    "swing_a_s": None,
                    "swing_b_s": None,
                    "ratio": None,
                    "percent_longer_b": None,
                    "message": f"Missing {name} boundaries on swing A.",
                }
            )
            continue
        sb = map_index(path, int(sa))
        eb = map_index(path, int(ea))
        dur_a = float(timestamps_a[int(ea)] - timestamps_a[int(sa)])
        dur_b = float(timestamps_b[int(eb)] - timestamps_b[int(sb)])
        if dur_a <= 1e-9:
            ratio = None
            pct = None
            message = f"{name}: swing A duration was ~0."
        else:
            ratio = dur_b / dur_a
            pct = (ratio - 1.0) * 100.0
            if abs(pct) < 5:
                message = f"{name} matched (within 5%)."
            elif pct > 0:
                message = f"Your {name} was {pct:.0f}% longer on swing 2."
            else:
                message = f"Your {name} was {abs(pct):.0f}% shorter on swing 2."
        out.append(
            {
                "name": name,
                "swing_a_s": dur_a,
                "swing_b_s": dur_b,
                "ratio": ratio,
                "percent_longer_b": pct,
                "message": message,
            }
        )
    return out

"""Signal helpers: One Euro filter, resampling, smoothing, derivatives."""

from __future__ import annotations

import numpy as np
from scipy.signal import savgol_filter


class OneEuroFilter:
    """1€ filter (Casiez, Roussel, Vogel 2012). Adapts cutoff to speed."""

    def __init__(
        self,
        min_cutoff: float = 1.0,
        beta: float = 0.007,
        dcutoff: float = 1.0,
    ) -> None:
        self.min_cutoff = min_cutoff
        self.beta = beta
        self.dcutoff = dcutoff
        self._x_prev: float | None = None
        self._dx_prev: float = 0.0
        self._t_prev: float | None = None

    @staticmethod
    def _alpha(dt: float, cutoff: float) -> float:
        tau = 1.0 / (2.0 * np.pi * cutoff)
        return 1.0 / (1.0 + tau / dt)

    def reset(self) -> None:
        self._x_prev = None
        self._dx_prev = 0.0
        self._t_prev = None

    def apply(self, x: float, t: float) -> float:
        if not np.isfinite(x):
            return x
        if self._x_prev is None or self._t_prev is None:
            self._x_prev = x
            self._t_prev = t
            return x
        dt = t - self._t_prev
        if dt <= 0:
            dt = 1e-6
        dx = (x - self._x_prev) / dt
        a_d = self._alpha(dt, self.dcutoff)
        dx_hat = a_d * dx + (1.0 - a_d) * self._dx_prev
        cutoff = self.min_cutoff + self.beta * abs(dx_hat)
        a = self._alpha(dt, cutoff)
        x_hat = a * x + (1.0 - a) * self._x_prev
        self._x_prev = x_hat
        self._dx_prev = dx_hat
        self._t_prev = t
        return x_hat


def filter_series(
    values: np.ndarray,
    timestamps: np.ndarray,
    min_cutoff: float = 1.0,
    beta: float = 0.007,
) -> np.ndarray:
    """Filter a 1D series, passing NaNs through without updating state."""
    out = np.empty_like(values, dtype=float)
    filt = OneEuroFilter(min_cutoff=min_cutoff, beta=beta)
    for i, (v, t) in enumerate(zip(values, timestamps, strict=True)):
        out[i] = filt.apply(float(v), float(t))
    return out


def filter_landmarks(
    xyz: np.ndarray,
    timestamps: np.ndarray,
    min_cutoff: float = 1.0,
    beta: float = 0.007,
) -> np.ndarray:
    """xyz: (N, 33, 3)."""
    n, n_lm, n_c = xyz.shape
    out = np.empty_like(xyz, dtype=float)
    for lm in range(n_lm):
        for c in range(n_c):
            out[:, lm, c] = filter_series(
                xyz[:, lm, c], timestamps, min_cutoff=min_cutoff, beta=beta
            )
    return out


def resample_series(t: np.ndarray, y: np.ndarray, t_new: np.ndarray) -> np.ndarray:
    """Linear interpolation, preserving NaNs when fewer than 2 valid samples."""
    y = np.asarray(y, dtype=float)
    valid = np.isfinite(y)
    if valid.sum() < 2:
        return np.full(t_new.shape, np.nan)
    return np.interp(t_new, t[valid], y[valid], left=np.nan, right=np.nan)


def resample_landmarks(
    t: np.ndarray, xyz: np.ndarray, vis: np.ndarray, t_new: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    n_lm = xyz.shape[1]
    xyz_new = np.empty((t_new.shape[0], n_lm, 3), dtype=float)
    vis_new = np.empty((t_new.shape[0], n_lm), dtype=float)
    for lm in range(n_lm):
        vis_new[:, lm] = resample_series(t, vis[:, lm], t_new)
        for c in range(3):
            xyz_new[:, lm, c] = resample_series(t, xyz[:, lm, c], t_new)
    return xyz_new, vis_new


def nan_savgol(y: np.ndarray, window: int = 13, poly: int = 3) -> np.ndarray:
    """Savitzky–Golay on a series with NaNs interpolated across short gaps."""
    y = np.asarray(y, dtype=float)
    n = y.size
    if n < window:
        window = n if n % 2 == 1 else max(n - 1, 1)
    if window < poly + 2:
        return y.copy()
    valid = np.isfinite(y)
    if valid.sum() < poly + 2:
        return y.copy()
    filled = y.copy()
    idx = np.arange(n)
    filled[~valid] = np.interp(idx[~valid], idx[valid], y[valid])
    smoothed = savgol_filter(filled, window_length=window, polyorder=poly, mode="interp")
    smoothed[~valid] = np.nan
    return smoothed


def smooth_then_diff(y: np.ndarray, dt: float, window: int = 13) -> np.ndarray:
    """Smooth first, then differentiate. Never differentiate raw jitter."""
    smoothed = nan_savgol(y, window=window)
    return np.gradient(smoothed, dt)


def mean_frame_jitter(xyz: np.ndarray, landmark: int) -> float:
    """Mean frame-to-frame displacement of one landmark (meters in world space)."""
    series = xyz[:, landmark, :]
    valid = np.all(np.isfinite(series), axis=1)
    pts = series[valid]
    if pts.shape[0] < 2:
        return float("nan")
    deltas = np.linalg.norm(np.diff(pts, axis=0), axis=1)
    return float(np.mean(deltas))

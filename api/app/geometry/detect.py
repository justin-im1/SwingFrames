from __future__ import annotations

from dataclasses import dataclass

import cv2
import numpy as np


@dataclass
class FittedLine:
    a: np.ndarray  # (x, y) pixels
    b: np.ndarray
    samples: np.ndarray  # (N, 2)

    @property
    def direction(self) -> np.ndarray:
        d = self.b - self.a
        n = np.linalg.norm(d)
        if n < 1e-6:
            return np.array([1.0, 0.0])
        return d / n


def included_angle_deg(d1: np.ndarray, d2: np.ndarray) -> float:
    u = d1 / max(np.linalg.norm(d1), 1e-9)
    v = d2 / max(np.linalg.norm(d2), 1e-9)
    c = float(np.clip(abs(np.dot(u, v)), 0.0, 1.0))
    return float(np.degrees(np.arccos(c)))


def _color_mask(bgr: np.ndarray) -> np.ndarray:
    hsv = cv2.cvtColor(bgr, cv2.COLOR_BGR2HSV)
    orange = cv2.inRange(hsv, (5, 70, 70), (22, 255, 255))
    yellow = cv2.inRange(hsv, (18, 70, 80), (40, 255, 255))
    mask = cv2.bitwise_or(orange, yellow)
    kernel = np.ones((5, 5), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    return mask


def _undirected_angle(p1: np.ndarray, p2: np.ndarray) -> float:
    ang = float(np.arctan2(p2[1] - p1[1], p2[0] - p1[0]))
    while ang > np.pi / 2:
        ang -= np.pi
    while ang < -np.pi / 2:
        ang += np.pi
    return ang


def _rho(p1: np.ndarray, p2: np.ndarray) -> float:
    d = p2 - p1
    n = np.array([-d[1], d[0]], dtype=float)
    ln = np.linalg.norm(n)
    if ln < 1e-6:
        return 0.0
    n /= ln
    return float(np.dot(p1, n))


def _cluster_segments(segs: list[tuple[np.ndarray, np.ndarray]]) -> list[list[tuple[np.ndarray, np.ndarray]]]:
    clusters: list[list[tuple[np.ndarray, np.ndarray]]] = []
    for a, b in segs:
        ang = _undirected_angle(a, b)
        rho = _rho(a, b)
        placed = False
        for cluster in clusters:
            ca, cb = cluster[0]
            if abs(_undirected_angle(ca, cb) - ang) < np.deg2rad(12) and abs(
                _rho(ca, cb) - rho
            ) < 28:
                cluster.append((a, b))
                placed = True
                break
        if not placed:
            clusters.append([(a, b)])
    return clusters


def _fit_line_from_points(pts: np.ndarray) -> FittedLine | None:
    if len(pts) < 8:
        return None
    pts = pts.astype(np.float64)
    mean = pts.mean(axis=0)
    centered = pts - mean
    _, _, vt = np.linalg.svd(centered, full_matrices=False)
    direction = vt[0]
    proj = centered @ direction
    a = mean + direction * proj.min()
    b = mean + direction * proj.max()
    # Near end = higher image y (closer to camera in a typical ground shot).
    if a[1] < b[1]:
        a, b = b, a
    ts = np.linspace(0.0, 1.0, 40)
    samples = np.outer(1 - ts, a) + np.outer(ts, b)
    return FittedLine(a=a, b=b, samples=samples)


def _pixels_near_line(
    mask: np.ndarray, a: np.ndarray, b: np.ndarray, band: float = 8.0
) -> np.ndarray:
    ys, xs = np.nonzero(mask)
    if len(xs) == 0:
        return np.zeros((0, 2))
    pts = np.stack([xs, ys], axis=1).astype(np.float64)
    d = b - a
    length = np.linalg.norm(d)
    if length < 1e-6:
        return np.zeros((0, 2))
    n = np.array([-d[1], d[0]]) / length
    dist = np.abs((pts - a) @ n)
    t = ((pts - a) @ d) / (length * length)
    keep = (dist < band) & (t > -0.05) & (t < 1.05)
    return pts[keep]


def detect_stick_lines(bgr: np.ndarray) -> list[FittedLine]:
    mask = _color_mask(bgr)
    edges = cv2.Canny(mask, 40, 120)
    h, w = mask.shape
    min_len = max(int(min(h, w) * 0.12), 24)
    raw = cv2.HoughLinesP(
        edges,
        rho=1,
        theta=np.pi / 180,
        threshold=30,
        minLineLength=min_len,
        maxLineGap=24,
    )
    if raw is None:
        return []
    segs = [(np.array([x1, y1], float), np.array([x2, y2], float)) for x1, y1, x2, y2 in raw[:, 0]]
    clusters = _cluster_segments(segs)
    lines: list[FittedLine] = []
    for cluster in clusters:
        acc_a = np.mean([p[0] for p in cluster], axis=0)
        acc_b = np.mean([p[1] for p in cluster], axis=0)
        nearby = _pixels_near_line(mask, acc_a, acc_b)
        fitted = _fit_line_from_points(nearby) if len(nearby) >= 8 else _fit_line_from_points(
            np.vstack(cluster)
        )
        if fitted is not None:
            lines.append(fitted)
    # Longest first; drop very short leftovers.
    lines.sort(key=lambda ln: np.linalg.norm(ln.b - ln.a), reverse=True)
    kept: list[FittedLine] = []
    for ln in lines:
        if np.linalg.norm(ln.b - ln.a) < min_len:
            continue
        duplicate = False
        for other in kept:
            if included_angle_deg(ln.direction, other.direction) < 8 and abs(
                _rho(ln.a, ln.b) - _rho(other.a, other.b)
            ) < 20:
                duplicate = True
                break
        if not duplicate:
            kept.append(ln)
    return kept


def line_from_endpoints(a: np.ndarray, b: np.ndarray) -> FittedLine:
    a = np.asarray(a, dtype=float)
    b = np.asarray(b, dtype=float)
    if a[1] < b[1]:
        a, b = b, a
    ts = np.linspace(0.0, 1.0, 40)
    samples = np.outer(1 - ts, a) + np.outer(ts, b)
    return FittedLine(a=a, b=b, samples=samples)

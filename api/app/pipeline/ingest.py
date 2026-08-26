"""Video ingest: metadata, fps gate, duration/resolution caps."""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field

import cv2
import numpy as np

from app.config import settings


class IngestError(ValueError):
    """Raised when a video cannot be used (e.g. below 60 fps)."""


@dataclass
class VideoMeta:
    fps: float
    frame_count: int
    duration_s: float
    width: int
    height: int
    quality_flags: list[dict] = field(default_factory=list)
    scaled_width: int = 0
    scaled_height: int = 0
    max_frames: int = 0


def _quality_flag(code: str, severity: str, message: str, **details) -> dict:
    return {"code": code, "severity": severity, "message": message, "details": details}


def read_meta(path: str) -> VideoMeta:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise IngestError("Could not open video file.")
    fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
    frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
    cap.release()
    if fps <= 0 or frame_count <= 0:
        raise IngestError("Video has no readable framerate or frames.")
    duration_s = frame_count / fps
    flags: list[dict] = []
    if fps < settings.min_fps:
        raise IngestError(
            f"Framerate {fps:.1f} fps is below the {settings.min_fps:.0f} fps "
            "minimum. A downswing is ~0.25s; 30 fps does not resolve a velocity peak."
        )
    if fps < settings.warn_fps:
        flags.append(
            _quality_flag(
                "low_fps",
                "warning",
                f"{fps:.0f} fps is usable but below 120 fps. Impact timing may be coarse.",
                fps=fps,
            )
        )
    if duration_s > settings.max_duration_s:
        flags.append(
            _quality_flag(
                "trimmed",
                "info",
                f"Video trimmed to the first {settings.max_duration_s:.0f}s.",
                original_duration_s=duration_s,
            )
        )
    long_side = max(width, height)
    scaled_w, scaled_h = width, height
    if long_side > settings.max_long_side:
        scale = settings.max_long_side / long_side
        scaled_w = max(2, int(width * scale) // 2 * 2)
        scaled_h = max(2, int(height * scale) // 2 * 2)
        flags.append(
            _quality_flag(
                "downscaled",
                "info",
                f"Frames downscaled from {width}x{height} to {scaled_w}x{scaled_h}.",
            )
        )
    max_frames = min(frame_count, int(settings.max_duration_s * fps))
    return VideoMeta(
        fps=fps,
        frame_count=frame_count,
        duration_s=duration_s,
        width=width,
        height=height,
        quality_flags=flags,
        scaled_width=scaled_w,
        scaled_height=scaled_h,
        max_frames=max_frames,
    )


def iter_frames(path: str, meta: VideoMeta) -> Iterator[np.ndarray]:
    cap = cv2.VideoCapture(path)
    if not cap.isOpened():
        raise IngestError("Could not open video file.")
    try:
        n = 0
        need_resize = (meta.scaled_width, meta.scaled_height) != (meta.width, meta.height)
        while n < meta.max_frames:
            ok, frame = cap.read()
            if not ok:
                break
            if need_resize:
                frame = cv2.resize(
                    frame,
                    (meta.scaled_width, meta.scaled_height),
                    interpolation=cv2.INTER_AREA,
                )
            yield frame
            n += 1
    finally:
        cap.release()

from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np

from app.media.ffmpeg import ffmpeg
from app.media.probe import ProbeResult, probe_file


async def transcode_to_h264(src: Path, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    await ffmpeg(
        "-y",
        "-i",
        str(src),
        "-c:v",
        "libx264",
        "-g",
        "2",
        "-keyint_min",
        "1",
        "-sc_threshold",
        "0",
        "-preset",
        "veryfast",
        "-crf",
        "23",
        "-an",
        "-pix_fmt",
        "yuv420p",
        "-movflags",
        "+faststart",
        str(dest),
        timeout=300.0,
    )


async def assert_no_rotation(path: Path) -> ProbeResult:
    probed = await probe_file(path)
    if probed.rotation is not None:
        raise RuntimeError(
            f"Rotation side-data remains on transcode ({probed.rotation}°)."
        )
    return probed


def distinct_frame_ratio(path: Path, max_compare: int = 90, thresh: float = 2.5) -> float:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("Could not open transcoded video.")
    prev: np.ndarray | None = None
    different = 0
    compared = 0
    try:
        while compared < max_compare:
            ok, frame = cap.read()
            if not ok:
                break
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            small = cv2.resize(gray, (160, 90), interpolation=cv2.INTER_AREA)
            if prev is not None:
                delta = np.abs(small.astype(np.float32) - prev.astype(np.float32))
                changed = float(np.mean(delta > 8.0))
                if changed > 0.001:
                    different += 1
                compared += 1
            prev = small
    finally:
        cap.release()
    if compared == 0:
        return 1.0
    return different / compared


def extract_frame_bgr(path: Path, frame_index: int, fps: float) -> np.ndarray:
    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError("Could not open video.")
    try:
        cap.set(cv2.CAP_PROP_POS_FRAMES, float(frame_index))
        ok, frame = cap.read()
        if ok and frame is not None:
            return frame
        t = (frame_index + 0.5) / max(fps, 1e-6)
        cap.set(cv2.CAP_PROP_POS_MSEC, t * 1000.0)
        ok, frame = cap.read()
        if not ok or frame is None:
            raise RuntimeError(f"Could not extract frame {frame_index}.")
        return frame
    finally:
        cap.release()

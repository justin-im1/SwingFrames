from __future__ import annotations

from pathlib import Path

import cv2
import numpy as np
import pytest

from app.pipeline.ingest import IngestError, read_meta


def _write_clip(path: Path, fps: float, n: int = 30, size: int = 64) -> None:
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (size, size))
    assert writer.isOpened()
    for i in range(n):
        frame = np.full((size, size, 3), i % 255, dtype=np.uint8)
        writer.write(frame)
    writer.release()


def test_rejects_below_60fps(tmp_path: Path) -> None:
    path = tmp_path / "slow.mp4"
    _write_clip(path, 30.0)
    with pytest.raises(IngestError, match="60"):
        read_meta(str(path))


def test_accepts_60fps_with_warning(tmp_path: Path) -> None:
    path = tmp_path / "ok.mp4"
    _write_clip(path, 60.0)
    meta = read_meta(str(path))
    assert meta.fps == pytest.approx(60.0, abs=0.5)
    codes = [f["code"] for f in meta.quality_flags]
    assert "low_fps" in codes


def test_120fps_has_no_low_fps_warning(tmp_path: Path) -> None:
    path = tmp_path / "fast.mp4"
    _write_clip(path, 120.0, n=40)
    meta = read_meta(str(path))
    assert meta.fps == pytest.approx(120.0, abs=1.0)
    codes = [f["code"] for f in meta.quality_flags]
    assert "low_fps" not in codes

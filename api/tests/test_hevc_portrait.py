from __future__ import annotations

from pathlib import Path

import pytest

from app.media.ffmpeg import FfmpegError, find_binary
from app.media.probe import probe_file
from app.media.transcode import assert_no_rotation, transcode_to_h264

ROOT = Path(__file__).resolve().parents[2]
HEVC = ROOT / "videos" / "GoodSwing.MOV"


def _have_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        return True
    except FfmpegError:
        return False


@pytest.mark.skipif(not HEVC.exists(), reason="GoodSwing.MOV not on disk")
@pytest.mark.skipif(not _have_ffmpeg(), reason="ffmpeg not available")
@pytest.mark.asyncio
async def test_iphone_hevc_portrait_bakes_rotation(tmp_path: Path) -> None:
    src_probe = await probe_file(HEVC)
    assert src_probe.codec in {"hevc", "h265"}
    assert src_probe.rotation is not None
    dest = tmp_path / "out.mp4"
    await transcode_to_h264(HEVC, dest)
    out = await assert_no_rotation(dest)
    assert out.rotation is None
    assert out.codec == "h264"
    assert out.height > out.width
    assert abs(out.fps - src_probe.fps) < 0.2

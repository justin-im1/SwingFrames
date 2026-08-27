from __future__ import annotations

from pathlib import Path

import pytest

from app.media.ffmpeg import FfmpegError, ffmpeg, find_binary
from app.media.probe import probe_file
from app.media.transcode import assert_no_rotation, transcode_to_h264


def _have_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        return True
    except FfmpegError:
        return False


needs_ffmpeg = pytest.mark.skipif(not _have_ffmpeg(), reason="ffmpeg not available")


@needs_ffmpeg
@pytest.mark.asyncio
async def test_transcode_dense_keyframes_and_measured_fps(tmp_path: Path) -> None:
    src = tmp_path / "src.mp4"
    dest = tmp_path / "out.mp4"
    await ffmpeg(
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=320x240:rate=30:duration=1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(src),
    )
    await transcode_to_h264(src, dest)
    probed = await assert_no_rotation(dest)
    assert probed.width == 320
    assert probed.height == 240
    assert probed.rotation is None
    assert abs(probed.fps - 30.0) < 0.6
    assert dest.exists() and dest.stat().st_size > 0


@needs_ffmpeg
@pytest.mark.asyncio
async def test_portrait_rotation_is_baked_in(tmp_path: Path) -> None:
    src = tmp_path / "portrait.mp4"
    dest = tmp_path / "out.mp4"
    try:
        await ffmpeg(
            "-y",
            "-f",
            "lavfi",
            "-i",
            "testsrc=size=640x360:rate=24:duration=1",
            "-c:v",
            "libx264",
            "-pix_fmt",
            "yuv420p",
            "-display_rotation",
            "90",
            "-an",
            str(src),
        )
    except FfmpegError:
        pytest.skip("This ffmpeg build does not support -display_rotation")
    src_probe = await probe_file(src)
    await transcode_to_h264(src, dest)
    probed = await assert_no_rotation(dest)
    assert probed.rotation is None
    if src_probe.rotation is not None:
        assert probed.height > probed.width
        assert {probed.width, probed.height} == {360, 640}

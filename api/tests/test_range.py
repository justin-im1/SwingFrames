from __future__ import annotations

from pathlib import Path

import pytest
from starlette.applications import Starlette
from starlette.responses import FileResponse
from starlette.routing import Route
from starlette.testclient import TestClient

from app.media.ffmpeg import FfmpegError, ffmpeg, find_binary


def _have_ffmpeg() -> bool:
    try:
        find_binary("ffmpeg")
        return True
    except FfmpegError:
        return False


needs_ffmpeg = pytest.mark.skipif(not _have_ffmpeg(), reason="ffmpeg not available")


@needs_ffmpeg
@pytest.mark.asyncio
async def test_file_response_honors_range(tmp_path: Path) -> None:
    clip = tmp_path / "tiny.mp4"
    await ffmpeg(
        "-y",
        "-f",
        "lavfi",
        "-i",
        "testsrc=size=160x120:rate=10:duration=1",
        "-c:v",
        "libx264",
        "-pix_fmt",
        "yuv420p",
        "-an",
        str(clip),
    )

    async def media(_request):
        return FileResponse(clip, media_type="video/mp4")

    app = Starlette(routes=[Route("/media", media)])
    with TestClient(app) as client:
        res = client.get("/media", headers={"Range": "bytes=0-1023"})
        assert res.status_code == 206
        assert res.headers.get("content-range", "").startswith("bytes 0-1023/")
        assert len(res.content) == 1024

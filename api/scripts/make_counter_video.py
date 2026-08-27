"""Generate the frame-counter clip used to verify browser seek.

Frame n shows n on screen. Validate in a browser, not with ffmpeg -ss.
"""

from __future__ import annotations

import asyncio
import shutil
import tempfile
from pathlib import Path

import cv2
import numpy as np

from app.media.ffmpeg import ffmpeg

ROOT = Path(__file__).resolve().parents[2]


async def main() -> None:
    out = ROOT / "storage" / "counter.mp4"
    out.parent.mkdir(parents=True, exist_ok=True)
    fps = 60
    n_frames = 10 * fps
    tmp = Path(tempfile.mkdtemp(prefix="sf-counter-"))
    try:
        for n in range(n_frames):
            img = np.full((480, 640, 3), 30, dtype=np.uint8)
            cv2.putText(
                img,
                str(n),
                (20, 90),
                cv2.FONT_HERSHEY_SIMPLEX,
                2.4,
                (255, 255, 255),
                4,
                cv2.LINE_AA,
            )
            cv2.imwrite(str(tmp / f"{n:05d}.png"), img)
        await ffmpeg(
            "-y",
            "-framerate",
            str(fps),
            "-i",
            str(tmp / "%05d.png"),
            "-c:v",
            "libx264",
            "-g",
            "2",
            "-keyint_min",
            "1",
            "-sc_threshold",
            "0",
            "-an",
            "-pix_fmt",
            "yuv420p",
            "-movflags",
            "+faststart",
            str(out),
            timeout=180.0,
        )
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    print(f"Wrote {out}")


if __name__ == "__main__":
    asyncio.run(main())

from __future__ import annotations

import asyncio
import logging
import uuid
from pathlib import Path

from app.config import settings
from app.db.models import Swing, TranscodeStatus
from app.db.session import AsyncSessionLocal
from app.media import (
    FfmpegError,
    assert_no_rotation,
    distinct_frame_ratio,
    probe_file,
    transcode_to_h264,
)

log = logging.getLogger(__name__)


async def process_swing(swing_id: uuid.UUID, upload_path: str) -> None:
    src = Path(upload_path)
    dest = settings.storage_path / f"{swing_id}.mp4"
    async with AsyncSessionLocal() as db:
        swing = await db.get(Swing, swing_id)
        if swing is None:
            return
        try:
            probed_in = await probe_file(src)
            if probed_in.duration_s > settings.max_duration_s:
                raise ValueError(
                    f"Clip is {probed_in.duration_s:.1f}s; max is {settings.max_duration_s:.0f}s."
                )
            await transcode_to_h264(src, dest)
            probed = await assert_no_rotation(dest)
            ratio = await asyncio.to_thread(distinct_frame_ratio, dest)
            swing.width = probed.width
            swing.height = probed.height
            swing.fps = probed.fps
            swing.frame_count = probed.packet_count
            swing.duration_s = probed.duration_s
            swing.distinct_frame_ratio = ratio
            swing.storage_path = str(dest)
            swing.transcode_status = TranscodeStatus.ready
            swing.error_message = None
        except (FfmpegError, ValueError, RuntimeError) as exc:
            log.exception("Transcode failed for %s", swing_id)
            swing.transcode_status = TranscodeStatus.failed
            swing.error_message = str(exc)
        except Exception as exc:  # noqa: BLE001 — persist failure, don't crash worker
            log.exception("Unexpected transcode error for %s", swing_id)
            swing.transcode_status = TranscodeStatus.failed
            swing.error_message = f"Transcode failed: {exc}"
        await db.commit()
    try:
        src.unlink(missing_ok=True)
    except OSError:
        pass

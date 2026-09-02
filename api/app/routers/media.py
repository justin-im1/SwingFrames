from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, StreamingResponse
from starlette.concurrency import iterate_in_threadpool

from app.db.models import TranscodeStatus
from app.db.session import AsyncSessionLocal
from app.deps import get_swing

router = APIRouter(tags=["media"])

CHUNK = 256 * 1024


def _byte_range(range_header: str, size: int) -> tuple[int, int] | None:
    if not range_header.lower().startswith("bytes="):
        return None
    spec = range_header.split("=", 1)[1].split(",")[0].strip()
    start_s, _, end_s = spec.partition("-")
    try:
        if start_s == "":
            suffix = int(end_s)
            if suffix <= 0:
                return None
            return max(0, size - suffix), size - 1
        start = int(start_s)
        end = int(end_s) if end_s else size - 1
    except ValueError:
        return None
    if start < 0 or start >= size:
        return None
    end = min(end, size - 1)
    if end < start:
        return None
    return start, end


def _iter_file(path: Path, start: int, length: int):
    with path.open("rb") as fh:
        fh.seek(start)
        remaining = length
        while remaining > 0:
            chunk = fh.read(min(CHUNK, remaining))
            if not chunk:
                break
            remaining -= len(chunk)
            yield chunk


@router.get("/api/media/{swing_id}")
async def get_media(swing_id: uuid.UUID, request: Request):
    async with AsyncSessionLocal() as db:
        swing = await get_swing(db, swing_id)
        if swing.transcode_status != TranscodeStatus.ready or not swing.storage_path:
            raise HTTPException(status_code=409, detail="Video is not ready.")
        path = Path(swing.storage_path)
        if not path.exists():
            raise HTTPException(status_code=404, detail="Media file missing.")
        storage_path = path

    size = storage_path.stat().st_size
    disposition = f'inline; filename="{swing_id}.mp4"'
    range_header = request.headers.get("range")
    if range_header:
        span = _byte_range(range_header, size)
        if span is None:
            raise HTTPException(
                status_code=416,
                headers={"Content-Range": f"bytes */{size}"},
                detail="Invalid range",
            )
        start, end = span
        length = end - start + 1
        return StreamingResponse(
            iterate_in_threadpool(_iter_file(storage_path, start, length)),
            status_code=206,
            media_type="video/mp4",
            headers={
                "Content-Range": f"bytes {start}-{end}/{size}",
                "Accept-Ranges": "bytes",
                "Content-Length": str(length),
                "Content-Disposition": disposition,
            },
        )
    return FileResponse(
        storage_path,
        media_type="video/mp4",
        filename=f"{swing_id}.mp4",
        content_disposition_type="inline",
        headers={"Accept-Ranges": "bytes"},
    )

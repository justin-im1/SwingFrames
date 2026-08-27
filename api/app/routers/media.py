from __future__ import annotations

import uuid
from pathlib import Path

from fastapi import APIRouter, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import Depends

from app.db.models import TranscodeStatus
from app.db.session import get_db
from app.deps import get_swing

router = APIRouter(tags=["media"])


@router.get("/api/media/{swing_id}")
async def get_media(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> FileResponse:
    swing = await get_swing(db, swing_id)
    if swing.transcode_status != TranscodeStatus.ready or not swing.storage_path:
        raise HTTPException(status_code=409, detail="Video is not ready.")
    path = Path(swing.storage_path)
    if not path.exists():
        raise HTTPException(status_code=404, detail="Media file missing.")
    return FileResponse(
        path,
        media_type="video/mp4",
        filename=f"{swing_id}.mp4",
        content_disposition_type="inline",
        stat_result=path.stat(),
    )

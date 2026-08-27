from __future__ import annotations

import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, UploadFile
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.db.models import Session, Swing, TranscodeStatus, User
from app.db.session import get_db
from app.deps import get_client_user, get_swing, require_session_owner, require_swing_owner
from app.jobs.transcode import process_swing
from app.models.schemas import SessionCreate, SessionDetail, SessionOut, SwingCreateResponse, SwingOut
from app.serialize import swing_out

router = APIRouter(tags=["swings"])


def _session_out(session: Session, n: int) -> SessionOut:
    return SessionOut(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        label=session.label,
        swing_count=n,
    )


@router.post("/api/sessions", response_model=SessionOut)
async def create_session(
    body: SessionCreate | None = None,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SessionOut:
    label = body.label if body else None
    if not label:
        label = datetime.now(timezone.utc).strftime("Session %b %d")
    session = Session(user_id=user.id, label=label)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return _session_out(session, 0)


@router.get("/api/sessions", response_model=list[SessionOut])
async def list_sessions(
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[SessionOut]:
    count = func.count(Swing.id)
    rows = await db.execute(
        select(Session, count)
        .outerjoin(Swing, Swing.session_id == Session.id)
        .where(Session.user_id == user.id)
        .group_by(Session.id)
        .order_by(Session.created_at.desc())
    )
    return [_session_out(session, int(n or 0)) for session, n in rows.all()]


@router.get("/api/sessions/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    result = await db.execute(
        select(Swing).where(Swing.session_id == session.id).order_by(Swing.created_at.asc())
    )
    swings = result.scalars().all()
    return SessionDetail(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        label=session.label,
        swing_count=len(swings),
        swings=[swing_out(s) for s in swings],
    )


@router.post("/api/swings", response_model=SwingCreateResponse)
async def upload_swing(
    file: UploadFile,
    background: BackgroundTasks,
    session_id: uuid.UUID | None = Form(default=None),
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SwingCreateResponse:
    if session_id is None:
        session = Session(
            user_id=user.id,
            label=datetime.now(timezone.utc).strftime("Session %b %d"),
        )
        db.add(session)
        await db.flush()
    else:
        session = await require_session_owner(db, user, session_id)

    suffix = Path(file.filename or "clip.mp4").suffix.lower() or ".mp4"
    if suffix not in {".mp4", ".mov", ".m4v", ".avi", ".webm", ".mkv"}:
        suffix = ".mp4"

    swing = Swing(
        session_id=session.id,
        filename=file.filename,
        transcode_status=TranscodeStatus.pending,
    )
    db.add(swing)
    await db.flush()

    dest_dir = settings.storage_path / "uploads"
    dest_dir.mkdir(parents=True, exist_ok=True)
    upload_path = dest_dir / f"{swing.id}{suffix}"
    size = 0
    with upload_path.open("wb") as out:
        while True:
            chunk = await file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > settings.max_upload_bytes:
                out.close()
                upload_path.unlink(missing_ok=True)
                raise HTTPException(status_code=413, detail="File too large.")
            out.write(chunk)

    await db.commit()
    await db.refresh(swing)
    background.add_task(process_swing, swing.id, str(upload_path))
    return SwingCreateResponse(
        id=swing.id,
        session_id=swing.session_id,
        transcode_status=swing.transcode_status.value,
    )


@router.get("/api/swings/{swing_id}", response_model=SwingOut)
async def get_swing_meta(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> SwingOut:
    swing = await get_swing(db, swing_id)
    return swing_out(swing)

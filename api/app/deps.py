from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session, Swing, User
from app.db.session import get_db


async def get_client_user(
    x_client_id: str = Header(..., alias="X-Client-Id"),
    db: AsyncSession = Depends(get_db),
) -> User:
    try:
        client_uuid = uuid.UUID(x_client_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="X-Client-Id must be a UUID.") from exc
    user = await db.get(User, client_uuid)
    if user is None:
        user = User(id=client_uuid)
        db.add(user)
        await db.commit()
        await db.refresh(user)
    return user


async def get_swing(db: AsyncSession, swing_id: uuid.UUID) -> Swing:
    swing = await db.get(Swing, swing_id)
    if swing is None:
        raise HTTPException(status_code=404, detail="Swing not found.")
    return swing


async def require_swing_owner(
    db: AsyncSession, user: User, swing_id: uuid.UUID
) -> Swing:
    swing = await get_swing(db, swing_id)
    session = await db.get(Session, swing.session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Swing not found.")
    return swing


async def get_session_by_id(db: AsyncSession, session_id: uuid.UUID) -> Session:
    session = await db.get(Session, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session


async def require_session_owner(
    db: AsyncSession, user: User, session_id: uuid.UUID
) -> Session:
    session = await get_session_by_id(db, session_id)
    if session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session

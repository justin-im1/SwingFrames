from __future__ import annotations

import uuid

from fastapi import Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Session, User
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


async def user_owns_session(db: AsyncSession, user: User, session_id: uuid.UUID) -> Session:
    session = await db.get(Session, session_id)
    if session is None or session.user_id != user.id:
        raise HTTPException(status_code=404, detail="Session not found.")
    return session

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Outcome, OutcomeResult, User
from app.db.session import get_db
from app.deps import get_client_user, get_swing, require_swing_owner
from app.models.schemas import OutcomeCreate, OutcomeOut

router = APIRouter(tags=["outcomes"])


@router.post("/api/swings/{swing_id}/outcome", response_model=OutcomeOut)
async def tag_outcome(
    swing_id: uuid.UUID,
    body: OutcomeCreate,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> OutcomeOut:
    await require_swing_owner(db, user, swing_id)
    existing = (
        await db.execute(select(Outcome).where(Outcome.swing_id == swing_id))
    ).scalar_one_or_none()
    if existing:
        existing.result = OutcomeResult(body.result)
        existing.note = body.note
        row = existing
    else:
        row = Outcome(
            swing_id=swing_id,
            result=OutcomeResult(body.result),
            note=body.note,
        )
        db.add(row)
    await db.commit()
    await db.refresh(row)
    return OutcomeOut(
        id=row.id,
        swing_id=row.swing_id,
        result=row.result.value,
        note=row.note,
        created_at=row.created_at,
    )


@router.get("/api/swings/{swing_id}/outcome", response_model=OutcomeOut | None)
async def get_outcome(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> OutcomeOut | None:
    await get_swing(db, swing_id)
    row = (
        await db.execute(select(Outcome).where(Outcome.swing_id == swing_id))
    ).scalar_one_or_none()
    if row is None:
        return None
    return OutcomeOut(
        id=row.id,
        swing_id=row.swing_id,
        result=row.result.value,
        note=row.note,
        created_at=row.created_at,
    )

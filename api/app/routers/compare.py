from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Comparison, Outcome, Swing, SyncMode, User
from app.db.session import get_db
from app.deps import get_client_user, get_session_by_id, require_swing_owner
from app.insights import build_insights
from app.models.schemas import ComparisonCreate, ComparisonOut, InsightsOut

router = APIRouter(tags=["compare"])


@router.post("/api/comparisons", response_model=ComparisonOut)
async def create_comparison(
    body: ComparisonCreate,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> ComparisonOut:
    await require_swing_owner(db, user, body.swing_a_id)
    await require_swing_owner(db, user, body.swing_b_id)
    row = Comparison(
        swing_a_id=body.swing_a_id,
        swing_b_id=body.swing_b_id,
        sync_mode=SyncMode(body.sync_mode),
        anchor_a=body.anchor_a,
        anchor_b=body.anchor_b,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return ComparisonOut(
        id=row.id,
        swing_a_id=row.swing_a_id,
        swing_b_id=row.swing_b_id,
        sync_mode=row.sync_mode.value,
        anchor_a=row.anchor_a,
        anchor_b=row.anchor_b,
        created_at=row.created_at,
    )


@router.get("/api/comparisons/{comparison_id}", response_model=ComparisonOut)
async def get_comparison(
    comparison_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> ComparisonOut:
    row = await db.get(Comparison, comparison_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Comparison not found.")
    return ComparisonOut(
        id=row.id,
        swing_a_id=row.swing_a_id,
        swing_b_id=row.swing_b_id,
        sync_mode=row.sync_mode.value,
        anchor_a=row.anchor_a,
        anchor_b=row.anchor_b,
        created_at=row.created_at,
    )


@router.get("/api/sessions/{session_id}/insights", response_model=InsightsOut)
async def session_insights(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> InsightsOut:
    session = await get_session_by_id(db, session_id)
    swings = (
        (
            await db.execute(
                select(Swing)
                .where(Swing.session_id == session.id)
                .order_by(Swing.created_at.asc())
            )
        )
        .scalars()
        .all()
    )
    ids = [s.id for s in swings]
    outcomes = (
        (await db.execute(select(Outcome).where(Outcome.swing_id.in_(ids)))).scalars().all()
        if ids
        else []
    )
    return build_insights(session.id, list(swings), list(outcomes))

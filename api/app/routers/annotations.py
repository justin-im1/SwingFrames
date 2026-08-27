from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Annotation, AnnotationKind, User
from app.db.session import get_db
from app.deps import get_client_user, get_swing, require_swing_owner
from app.models.schemas import AnnotationCreate, AnnotationOut
from app.serialize import annotation_out

router = APIRouter(tags=["annotations"])


@router.get("/api/swings/{swing_id}/annotations", response_model=list[AnnotationOut])
async def list_annotations(
    swing_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationOut]:
    await get_swing(db, swing_id)
    rows = await db.execute(
        select(Annotation)
        .where(Annotation.swing_id == swing_id)
        .order_by(Annotation.created_at.asc())
    )
    return [annotation_out(r) for r in rows.scalars().all()]


@router.post("/api/swings/{swing_id}/annotations", response_model=AnnotationOut)
async def create_annotation(
    swing_id: uuid.UUID,
    body: AnnotationCreate,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> AnnotationOut:
    await require_swing_owner(db, user, swing_id)
    row = Annotation(
        swing_id=swing_id,
        frame=body.frame,
        kind=AnnotationKind(body.kind),
        points=[p.model_dump() for p in body.points],
        style=body.style,
        label=body.label,
        sticky=body.sticky,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return annotation_out(row)


@router.delete("/api/annotations/{annotation_id}", status_code=204)
async def delete_annotation(
    annotation_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    row = await db.get(Annotation, annotation_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Annotation not found.")
    await require_swing_owner(db, user, row.swing_id)
    await db.delete(row)
    await db.commit()

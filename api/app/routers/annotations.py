from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Annotation, AnnotationKind, User
from app.db.session import get_db
from app.deps import get_client_user, get_swing, require_swing_owner
from app.models.schemas import AnnotationCopy, AnnotationCreate, AnnotationOut
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


@router.post("/api/swings/{swing_id}/annotations/copy", response_model=list[AnnotationOut])
async def copy_annotations(
    swing_id: uuid.UUID,
    body: AnnotationCopy,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> list[AnnotationOut]:
    await require_swing_owner(db, user, swing_id)
    if body.source_id == swing_id:
        return []
    await require_swing_owner(db, user, body.source_id)
    q = select(Annotation).where(Annotation.swing_id == body.source_id)
    if body.annotation_ids:
        q = q.where(Annotation.id.in_(body.annotation_ids))
    q = q.order_by(Annotation.created_at.asc())
    rows = (await db.execute(q)).scalars().all()
    created: list[Annotation] = []
    for src in rows:
        clone = Annotation(
            swing_id=swing_id,
            frame=body.target_frame,
            kind=src.kind,
            points=list(src.points),
            style=src.style,
            label=src.label,
            sticky=src.sticky,
        )
        db.add(clone)
        created.append(clone)
    await db.commit()
    for row in created:
        await db.refresh(row)
    return [annotation_out(row) for row in created]


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


@router.delete("/api/swings/{swing_id}/annotations", status_code=204)
async def clear_annotations(
    swing_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await require_swing_owner(db, user, swing_id)
    await db.execute(delete(Annotation).where(Annotation.swing_id == swing_id))
    await db.commit()

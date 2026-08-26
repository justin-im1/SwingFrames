from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Session, Swing, SwingStatus, User
from app.db.session import get_db
from app.deps import get_client_user, user_owns_session
from app.models.schemas import (
    ConsistencyMetric,
    ConsistencyOut,
    SessionCreate,
    SessionDetail,
    SessionOut,
    SwingSummary,
)

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


def swing_summary(swing: Swing) -> SwingSummary:
    return SwingSummary(
        id=swing.id,
        session_id=swing.session_id,
        created_at=swing.created_at,
        status=swing.status.value,
        source_fps=swing.source_fps,
        frame_count=swing.frame_count,
        duration_s=swing.duration_s,
        view_class=swing.view_class.value,
        view_confidence=swing.view_confidence,
        quality_flags=swing.quality_flags or [],
        is_usable=swing.is_usable,
        error_message=swing.error_message,
        handedness=swing.handedness.value,
        view_flagged_wrong=swing.view_flagged_wrong,
    )


@router.post("", response_model=SessionOut)
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
    return SessionOut(
        id=session.id,
        user_id=session.user_id,
        created_at=session.created_at,
        label=session.label,
        swing_count=0,
    )


@router.get("", response_model=list[SessionOut])
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
    return [
        SessionOut(
            id=session.id,
            user_id=session.user_id,
            created_at=session.created_at,
            label=session.label,
            swing_count=int(n or 0),
        )
        for session, n in rows.all()
    ]


@router.get("/{session_id}", response_model=SessionDetail)
async def get_session(
    session_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> SessionDetail:
    session = await user_owns_session(db, user, session_id)
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
        swings=[swing_summary(s) for s in swings],
    )


def _cv(values: list[float]) -> tuple[float | None, float | None, float | None]:
    if not values:
        return None, None, None
    mean = sum(values) / len(values)
    var = sum((v - mean) ** 2 for v in values) / len(values)
    std = var**0.5
    cv = std / abs(mean) if abs(mean) > 1e-9 else None
    return mean, std, cv


def _impact_time(swing: Swing) -> float | None:
    if swing.phases is None or swing.features is None:
        return None
    ts = swing.features.timestamps
    idx = swing.phases.impact_idx
    if idx is None or ts is None or idx >= len(ts):
        return None
    return float(ts[idx])


@router.get("/{session_id}/consistency", response_model=ConsistencyOut)
async def session_consistency(
    session_id: uuid.UUID,
    user: User = Depends(get_client_user),
    db: AsyncSession = Depends(get_db),
) -> ConsistencyOut:
    session = await user_owns_session(db, user, session_id)
    result = await db.execute(
        select(Swing)
        .options(
            selectinload(Swing.metrics),
            selectinload(Swing.phases),
            selectinload(Swing.features),
        )
        .where(Swing.session_id == session.id, Swing.status == SwingStatus.ready)
        .order_by(Swing.created_at.asc())
    )
    swings = [
        s
        for s in result.scalars().all()
        if s.is_usable and s.metrics and s.phases and s.features
    ]
    n = len(swings)
    if n < 3:
        return ConsistencyOut(
            session_id=session.id,
            n=n,
            usable_n=n,
            ready=False,
            message=(
                f"Consistency needs at least 3 usable swings in this session "
                f"(you have {n}). Five or more is better."
            ),
        )

    def rel_peak(swing: Swing, peak: float | None) -> float | None:
        imp = _impact_time(swing)
        if peak is None or imp is None:
            return None
        return peak - imp

    series: list[tuple[str, list[float | None]]] = [
        ("tempo_ratio", [s.metrics.tempo_ratio for s in swings]),
        (
            "pelvis_peak_to_impact_s",
            [rel_peak(s, s.metrics.pelvis_peak_time_s) for s in swings],
        ),
        (
            "torso_peak_to_impact_s",
            [rel_peak(s, s.metrics.torso_peak_time_s) for s in swings],
        ),
        (
            "arm_peak_to_impact_s",
            [rel_peak(s, s.metrics.arm_peak_time_s) for s in swings],
        ),
        ("pelvis_torso_gap_ms", [s.metrics.pelvis_torso_gap_ms for s in swings]),
        ("torso_arm_gap_ms", [s.metrics.torso_arm_gap_ms for s in swings]),
    ]

    metrics_out: list[ConsistencyMetric] = []
    least_name: str | None = None
    least_cv = -1.0
    for name, values in series:
        finite = [v for v in values if v is not None]
        mean, std, cv = _cv(finite)
        metrics_out.append(
            ConsistencyMetric(
                name=name, mean=mean, std=std, cv=cv, n=len(finite), values=values
            )
        )
        if cv is not None and cv > least_cv:
            least_cv = cv
            least_name = name

    extra = " Five or more is better." if n < 5 else ""
    return ConsistencyOut(
        session_id=session.id,
        n=n,
        usable_n=n,
        ready=True,
        message=f"Coefficient of variation across {n} usable swings.{extra}",
        metrics=metrics_out,
        least_repeatable=least_name,
    )

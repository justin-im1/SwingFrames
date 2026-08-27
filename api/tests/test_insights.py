from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.models import AimMeasurement, AimMethod, CameraView, Outcome, OutcomeResult, Swing
from app.insights import MIN_TAGGED, build_insights


def _swing() -> Swing:
    return Swing(id=uuid.uuid4(), session_id=uuid.uuid4())


def _outcome(swing_id, result: OutcomeResult) -> Outcome:
    return Outcome(
        id=uuid.uuid4(),
        swing_id=swing_id,
        result=result,
        created_at=datetime.now(timezone.utc),
    )


def _aim(swing_id, deg: float) -> AimMeasurement:
    return AimMeasurement(
        id=uuid.uuid4(),
        swing_id=swing_id,
        method=AimMethod.toe_stick,
        view=CameraView.face_on,
        feet_angle_deg=deg,
        error_band_deg=1.0,
        created_at=datetime.now(timezone.utc),
    )


def test_insights_below_threshold() -> None:
    swings = [_swing() for _ in range(5)]
    outcomes = [_outcome(s.id, OutcomeResult.slice) for s in swings]
    out = build_insights(uuid.uuid4(), swings, outcomes, [])
    assert out.ready is False
    assert out.tagged_n == 5
    assert out.lines == []


def test_insights_slice_aimed_left() -> None:
    swings = [_swing() for _ in range(MIN_TAGGED)]
    outcomes = [_outcome(s.id, OutcomeResult.slice) for s in swings]
    aims = [_aim(s.id, -4.0) for s in swings]
    sid = uuid.uuid4()
    out = build_insights(sid, swings, outcomes, aims)
    assert out.ready is True
    assert any("aimed left" in line.text and "slice" in line.text for line in out.lines)
    assert "not a cause" in out.message

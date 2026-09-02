from __future__ import annotations

import uuid
from datetime import datetime, timezone

from app.db.models import Outcome, OutcomeResult, Swing
from app.insights import build_insights


def _swing() -> Swing:
    return Swing(id=uuid.uuid4(), session_id=uuid.uuid4())


def _outcome(swing_id, result: OutcomeResult) -> Outcome:
    return Outcome(
        id=uuid.uuid4(),
        swing_id=swing_id,
        result=result,
        created_at=datetime.now(timezone.utc),
    )


def test_insights_empty() -> None:
    out = build_insights(uuid.uuid4(), [_swing() for _ in range(3)], [])
    assert out.ready is False
    assert out.tagged_n == 0
    assert out.lines == []


def test_insights_counts_by_outcome() -> None:
    swings = [_swing() for _ in range(3)]
    outcomes = [
        _outcome(swings[0].id, OutcomeResult.slice),
        _outcome(swings[1].id, OutcomeResult.slice),
        _outcome(swings[2].id, OutcomeResult.hook),
    ]
    out = build_insights(uuid.uuid4(), swings, outcomes)
    assert out.ready is True
    assert out.tagged_n == 3
    assert any("2 tagged slice" in line.text for line in out.lines)
    assert any("1 tagged hook" in line.text for line in out.lines)

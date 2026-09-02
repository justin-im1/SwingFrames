from __future__ import annotations

from collections import Counter

from app.db.models import Outcome, Swing
from app.models.schemas import InsightLine, InsightsOut


def build_insights(session_id, swings: list[Swing], outcomes: list[Outcome]) -> InsightsOut:
    n = len(outcomes)
    if n == 0:
        return InsightsOut(
            session_id=session_id,
            tagged_n=0,
            ready=False,
            message="Tag ball flight on swings to see counts for this session.",
        )
    counts = Counter(o.result for o in outcomes)
    lines = [
        InsightLine(
            text=f"{count} tagged {result.value}",
            n=count,
            outcome=result.value,
        )
        for result, count in counts.most_common()
    ]
    return InsightsOut(
        session_id=session_id,
        tagged_n=n,
        ready=True,
        message=f"{n} tagged swing{'s' if n != 1 else ''} in this session.",
        lines=lines,
    )

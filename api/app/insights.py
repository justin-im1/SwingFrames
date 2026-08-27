from __future__ import annotations

from collections import defaultdict

from app.db.models import AimMeasurement, Outcome, OutcomeResult, Swing
from app.models.schemas import InsightLine, InsightsOut


MIN_TAGGED = 8
MIN_PER_OUTCOME = 3


def _aimed_left(aim: AimMeasurement) -> bool:
    if aim.feet_angle_deg is None:
        return False
    band = aim.error_band_deg or 1.0
    return aim.feet_angle_deg < -band


def _aimed_right(aim: AimMeasurement) -> bool:
    if aim.feet_angle_deg is None:
        return False
    band = aim.error_band_deg or 1.0
    return aim.feet_angle_deg > band


def build_insights(
    session_id, swings: list[Swing], outcomes: list[Outcome], aims: list[AimMeasurement]
) -> InsightsOut:
    aim_by_swing = {}
    for aim in sorted(aims, key=lambda a: a.created_at):
        aim_by_swing[aim.swing_id] = aim
    outcome_by_swing = {o.swing_id: o for o in outcomes}

    tagged: list[tuple[Swing, Outcome, AimMeasurement | None]] = []
    for swing in swings:
        outcome = outcome_by_swing.get(swing.id)
        if outcome is None:
            continue
        tagged.append((swing, outcome, aim_by_swing.get(swing.id)))

    n = len(tagged)
    if n < MIN_TAGGED:
        return InsightsOut(
            session_id=session_id,
            tagged_n=n,
            ready=False,
            message=(
                f"Need at least {MIN_TAGGED} tagged swings before showing correlations "
                f"(you have {n})."
            ),
        )

    by_result: dict[OutcomeResult, list[tuple[Swing, Outcome, AimMeasurement | None]]] = (
        defaultdict(list)
    )
    for row in tagged:
        by_result[row[1].result].append(row)

    lines: list[InsightLine] = []
    for result, rows in by_result.items():
        if len(rows) < MIN_PER_OUTCOME:
            continue
        with_aim = [r for r in rows if r[2] is not None and r[2].feet_angle_deg is not None]
        if len(with_aim) < MIN_PER_OUTCOME:
            continue
        left_n = sum(1 for _, _, aim in with_aim if aim and _aimed_left(aim))
        right_n = sum(1 for _, _, aim in with_aim if aim and _aimed_right(aim))
        total = len(with_aim)
        label = result.value
        if left_n >= MIN_PER_OUTCOME and left_n >= total / 2:
            lines.append(
                InsightLine(
                    text=f"You aimed left of target on {left_n} of your last {total} {label}s.",
                    n=left_n,
                    outcome=result.value,
                )
            )
        if right_n >= MIN_PER_OUTCOME and right_n >= total / 2:
            lines.append(
                InsightLine(
                    text=f"You aimed right of target on {right_n} of your last {total} {label}s.",
                    n=right_n,
                    outcome=result.value,
                )
            )

        others = [
            r[2].feet_angle_deg
            for r in tagged
            if r[1].result != result
            and r[2] is not None
            and r[2].feet_angle_deg is not None
        ]
        these = [r[2].feet_angle_deg for r in with_aim if r[2] is not None]
        if len(these) >= MIN_PER_OUTCOME and len(others) >= MIN_PER_OUTCOME:
            mean_these = sum(these) / len(these)
            mean_others = sum(others) / len(others)
            delta = mean_these - mean_others
            if abs(delta) >= 1.0:
                direction = "right" if delta > 0 else "left"
                lines.append(
                    InsightLine(
                        text=(
                            f"Your aim was {abs(delta):.1f}° more {direction} of target "
                            f"on average when the ball {label}d, among tagged swings in this session."
                        ),
                        n=len(these),
                        outcome=result.value,
                    )
                )

    if not lines:
        return InsightsOut(
            session_id=session_id,
            tagged_n=n,
            ready=True,
            message=(
                f"{n} tagged swings, but no setup factor had at least "
                f"{MIN_PER_OUTCOME} samples of a given outcome to compare."
            ),
        )
    return InsightsOut(
        session_id=session_id,
        tagged_n=n,
        ready=True,
        message="Observed correlations for this golfer — not a cause of ball flight.",
        lines=lines,
    )

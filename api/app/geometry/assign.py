from __future__ import annotations

from dataclasses import dataclass

from app.geometry.detect import FittedLine, included_angle_deg


class LineAssignError(ValueError):
    pass


@dataclass
class AssignedLines:
    calib: list[FittedLine]
    toe: FittedLine | None
    message: str


def assign_lines(lines: list[FittedLine]) -> AssignedLines:
    n = len(lines)
    if n < 2:
        raise LineAssignError(
            "Not enough alignment sticks found. Need two parallel calibration sticks."
        )
    if n > 3:
        raise LineAssignError(
            f"Found {n} lines. Recapture or nudge to keep two calibration sticks "
            "and an optional toe stick — extra clubs and shadows confuse detection."
        )
    if n == 2:
        return AssignedLines(
            calib=lines,
            toe=None,
            message="Two sticks detected. Treat as the calibration pair.",
        )

    pairs = [(0, 1), (0, 2), (1, 2)]
    scores: list[tuple[float, int, int]] = []
    for i, j in pairs:
        ang = included_angle_deg(lines[i].direction, lines[j].direction)
        scores.append((ang, i, j))
    scores.sort()
    best, i, j = scores[0]
    second = scores[1][0]
    if best > 28.0:
        raise LineAssignError(
            "Could not find a clearly parallel calibration pair. "
            "Lay two sticks parallel to the target line."
        )
    if second - best < 8.0:
        raise LineAssignError(
            "Stick assignment is ambiguous — no pair is clearly more parallel "
            "than the others. Nudge the detected lines or recapture."
        )
    k = ({0, 1, 2} - {i, j}).pop()
    return AssignedLines(
        calib=[lines[i], lines[j]],
        toe=lines[k],
        message="Three sticks: most-parallel pair is calibration; odd one out is the toe stick.",
    )

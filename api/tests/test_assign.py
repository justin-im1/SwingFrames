from __future__ import annotations

import numpy as np
import pytest

from app.geometry.assign import LineAssignError, assign_lines
from app.geometry.detect import FittedLine


def _line(a, b) -> FittedLine:
    a = np.array(a, dtype=float)
    b = np.array(b, dtype=float)
    ts = np.linspace(0.0, 1.0, 40)
    samples = np.outer(1 - ts, a) + np.outer(ts, b)
    return FittedLine(a=a, b=b, samples=samples)


def test_three_lines_most_parallel_are_calib() -> None:
    calib_a = _line((100, 400), (120, 40))
    calib_b = _line((180, 400), (200, 40))
    toe = _line((60, 360), (240, 350))
    assigned = assign_lines([calib_a, toe, calib_b])
    assert assigned.toe is toe
    assert set(map(id, assigned.calib)) == {id(calib_a), id(calib_b)}


def test_two_lines_are_calib() -> None:
    a = _line((100, 400), (110, 40))
    b = _line((200, 400), (210, 40))
    assigned = assign_lines([a, b])
    assert assigned.toe is None
    assert assigned.calib == [a, b]


def test_one_line_rejects() -> None:
    with pytest.raises(LineAssignError, match="Not enough"):
        assign_lines([_line((10, 10), (100, 100))])


def test_four_lines_rejects() -> None:
    lines = [_line((i * 40, 400), (i * 40 + 10, 40)) for i in range(4)]
    with pytest.raises(LineAssignError, match="Found 4"):
        assign_lines(lines)


def test_ambiguous_three_rejects() -> None:
    # Three nearly-parallel sticks: no odd one out.
    a = _line((100, 400), (110, 40))
    b = _line((180, 400), (195, 40))
    c = _line((260, 400), (268, 40))
    with pytest.raises(LineAssignError, match="ambiguous"):
        assign_lines([a, b, c])

from __future__ import annotations

import pytest

from app.pipeline.pose import extract_pose


def test_pose_import_or_skip() -> None:
    pytest.importorskip("mediapipe")
    assert callable(extract_pose)

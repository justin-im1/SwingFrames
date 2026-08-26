import json
from pathlib import Path

import pytest

LABELS = Path(__file__).parent / "fixtures" / "LABELS.json"


def test_labelled_fixtures_optional() -> None:
    data = json.loads(LABELS.read_text())
    clips = data.get("clips") or {}
    if not clips:
        pytest.skip("No labelled real clips in tests/fixtures/LABELS.json")

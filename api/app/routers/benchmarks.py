"""Published tempo figures — not from licensed pro video.

Tour ~3:1 is the commonly cited PGA Tour address-to-top vs top-to-impact split
(~0.75s / ~0.25s). Individual names are approximate published reports.
"""

from fastapi import APIRouter

from app.models.schemas import ProBenchmark

router = APIRouter(prefix="/api/benchmarks", tags=["benchmarks"])

PROS: list[ProBenchmark] = [
    ProBenchmark(
        id="tour_average",
        name="Tour average",
        tempo_ratio=3.0,
        backswing_s=0.75,
        downswing_s=0.25,
        source="Commonly cited PGA Tour tempo (~3:1).",
    ),
    ProBenchmark(
        id="hogan",
        name="Ben Hogan (reported)",
        tempo_ratio=3.0,
        backswing_s=0.75,
        downswing_s=0.25,
        source="Widely reported 3:1 Hogan tempo; not measured from video here.",
    ),
    ProBenchmark(
        id="slower",
        name="Deliberate 4:1",
        tempo_ratio=4.0,
        backswing_s=1.00,
        downswing_s=0.25,
        source="Reference slower-backswing profile.",
    ),
]


@router.get("/pros", response_model=list[ProBenchmark])
async def list_pros() -> list[ProBenchmark]:
    return PROS

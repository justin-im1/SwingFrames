from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import benchmarks, comparisons, sessions, swings

app = FastAPI(
    title="SwingFrames API",
    version="0.1.0",
    description="View-invariant golf swing timing analysis.",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(swings.router)
app.include_router(sessions.router)
app.include_router(comparisons.router)
app.include_router(benchmarks.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}

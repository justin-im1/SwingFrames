from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import annotations, compare, measure, media, swings

app = FastAPI(
    title="SwingFrames API",
    version="0.2.0",
    description="Golf swing video review — frame-accurate playback and annotation.",
)


app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Accept-Ranges", "Content-Range", "Content-Length"],
)

app.include_router(swings.router)
app.include_router(media.router)
app.include_router(annotations.router)
app.include_router(measure.router)
app.include_router(compare.router)


@app.get("/api/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


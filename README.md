# SwingFrames

Golf swing video review. Frame-accurate playback, persistent annotation, and side-by-side compare.

It does **not** estimate pose, score swing quality, track the clubface, measure aim, or predict ball flight.

## What it does

- **Playback** with frame-accurate stepping on transcoded H.264.
- **Drawings** (lines, angles, circles, paths) in normalized coordinates, sticky across frames or on one frame.
- **Outcome tags** (slice, hook, …) as *your* observation. Session page shows tag counts, not causes.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind 4, Canvas 2D |
| Backend | FastAPI, Python 3.11+ |
| Media | ffmpeg via `asyncio.create_subprocess_exec` |
| DB | PostgreSQL 16, SQLAlchemy 2, Alembic |
| Identity | Anonymous `X-Client-Id` cookie (`sf_client_id`) |

No accounts. Session and swing URLs are capability links: **anyone with the link can watch the video**. Writes require the cookie. Clearing cookies loses write access; there is no cross-device continuity.

## Run locally

You need Docker (Postgres), Python 3.11+, Node 20+. ffmpeg on `PATH` is preferred (`brew install ffmpeg`); otherwise the API uses the `imageio-ffmpeg` binary.

```bash
# database
docker compose up -d db

# api
cd api
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
alembic upgrade head
uvicorn app.main:app --reload --port 8000

# web (second terminal)
cd web
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000). Next.js proxies `/api/*` to FastAPI.

## Frame accuracy

Uploads are transcoded to H.264 with `-g 2` (nearly every frame a keyframe), audio dropped, rotation baked in. fps is `nb_read_packets / duration` from ffprobe, never container `r_frame_rate`.

Generate the counter clip and step it in a **browser** (not with ffmpeg `-ss`):

```bash
cd api && python scripts/make_counter_video.py
```

Upload `storage/counter.mp4`. The on-screen number must match the UI frame index at every step.

## Tests

```bash
cd api
source .venv/bin/activate
pytest
```

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/swings` | Upload; returns `pending` |
| GET | `/api/swings/{id}` | Metadata, measured fps, quality flags |
| GET | `/api/media/{id}` | Video bytes; HTTP Range required |
| GET/POST | `/api/swings/{id}/annotations` | Per-frame drawings (normalized coords) |
| DELETE | `/api/annotations/{id}` | |
| POST | `/api/swings/{id}/outcome` | Tag ball flight |
| GET | `/api/sessions/{id}/insights` | Outcome tag counts |
| POST | `/api/comparisons` | Persist a pair + sync mode |

# SwingFrames

Golf swing analysis from phone video. The product measures **timing and consistency**, not “swing quality.” Positional comparison only unlocks when two swings share a view class.

Video is processed, then **discarded**. Analysis outputs (a few hundred KB of time series) are what persist.

## Constraints

- **60 fps minimum**, 120 fps preferred. A downswing is ~0.25s; 30 fps cannot resolve a velocity peak.
- Angles come from MediaPipe **world landmarks**, never normalized 2D.
- DTW is implemented by hand — no `dtaidistance`, no `fastdtw`.
- No accounts. Identity is an anonymous `X-Client-Id` cookie (`sf_client_id`). Clearing cookies loses history; there is no cross-device continuity. Fine for a demo.

## Stack

| Layer | Choice |
|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind 4 |
| Backend | FastAPI, Python 3.11+ |
| Pose | MediaPipe Pose (`pose_world_landmarks`) |
| DB | PostgreSQL 16, SQLAlchemy 2, Alembic |

## Run locally

You need Docker (Postgres), Python 3.11+, Node 20+.

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

Open [http://localhost:3000](http://localhost:3000). The Next.js app proxies `/api/*` to FastAPI.

## Tests

```bash
cd api
source .venv/bin/activate
pytest
```

Unit tests cover ingest fps gates, One Euro jitter reduction, view classification, synthetic segmentation/tempo, and DTW known-answer cases (identical series, time-stretched copy, the mean-deviation trap).

Drop labelled real clips in `api/tests/fixtures/` and list them in `LABELS.json` to enable the optional labelled-fixture test. Large videos are gitignored.

## API

| Method | Path | Purpose |
|---|---|---|
| POST | `/api/swings` | Upload video (async job) |
| GET | `/api/swings/{id}` | Status, view class, quality flags |
| GET | `/api/swings/{id}/metrics` | Tempo, sequence |
| GET | `/api/swings/{id}/features` | Time series |
| POST | `/api/comparisons` | DTW two swings |
| GET | `/api/sessions/{id}/consistency` | CV across a session |
| GET | `/api/benchmarks/pros` | Static tempo table |

Pro numbers are published tempo figures, not measurements from licensed broadcast video.

## Pipeline

`ingest → pose → clean → normalize → view → segment → analyze` (+ `dtw` on compare).

Quality flags always surface in the UI. A metric computed over gated-out landmarks is reported as unreliable, never as a silent number.

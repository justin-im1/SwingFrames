from __future__ import annotations

import uuid

import pytest
from httpx import ASGITransport, AsyncClient

from app.db.models import Annotation, AnnotationKind, Session, Swing, TranscodeStatus, User
from app.db.session import AsyncSessionLocal
from app.main import app


@pytest.mark.asyncio
async def test_copy_annotations_keeps_normalized_points() -> None:
    cid = uuid.uuid4()
    async with AsyncSessionLocal() as db:
        db.add(User(id=cid))
        session = Session(user_id=cid)
        db.add(session)
        await db.flush()
        source = Swing(
            session_id=session.id,
            filename="a.mp4",
            transcode_status=TranscodeStatus.ready,
        )
        target = Swing(
            session_id=session.id,
            filename="b.mp4",
            transcode_status=TranscodeStatus.ready,
        )
        db.add_all([source, target])
        await db.flush()
        points = [{"x": 0.2, "y": 0.3}, {"x": 0.8, "y": 0.9}]
        db.add(
            Annotation(
                swing_id=source.id,
                frame=12,
                kind=AnnotationKind.line,
                points=points,
                sticky=True,
            )
        )
        db.add(
            Annotation(
                swing_id=source.id,
                frame=4,
                kind=AnnotationKind.circle,
                points=[{"x": 0.5, "y": 0.5}],
                sticky=False,
            )
        )
        await db.commit()
        source_id, target_id = source.id, target.id

    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        res = await client.post(
            f"/api/swings/{target_id}/annotations/copy",
            headers={"X-Client-Id": str(cid)},
            json={"source_id": str(source_id), "target_frame": 7},
        )
        same = await client.post(
            f"/api/swings/{source_id}/annotations/copy",
            headers={"X-Client-Id": str(cid)},
            json={"source_id": str(source_id), "target_frame": 0},
        )

    assert res.status_code == 200, res.text
    body = res.json()
    assert len(body) == 2
    assert all(row["swing_id"] == str(target_id) for row in body)
    line = next(row for row in body if row["kind"] == "line")
    assert line["points"] == points
    assert line["sticky"] is True
    assert line["frame"] == 7
    circle = next(row for row in body if row["kind"] == "circle")
    assert circle["sticky"] is False
    assert circle["frame"] == 7
    assert same.status_code == 200
    assert same.json() == []

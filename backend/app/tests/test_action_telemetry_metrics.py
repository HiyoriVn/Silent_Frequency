"""
Batch 4.3 telemetry metrics tests.

Validates lightweight metric increments for trace trimming paths.
"""

from __future__ import annotations

import json
import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from backend.app import metrics
from backend.app.config import get_settings
from backend.app.db.database import Base, get_db
from backend.app.db.models import Puzzle, PuzzleVariant, RoomTemplate, Skill
from backend.app.main import app
from backend.app.seed import PUZZLES, ROOM_TEMPLATES, SKILLS, VARIANTS


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


TEST_DB_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def v2_flag_and_metrics_reset():
    prev = os.environ.get("GAMEPLAY_V2_ENABLED")
    os.environ["GAMEPLAY_V2_ENABLED"] = "true"
    get_settings.cache_clear()
    metrics.reset_counters()
    yield
    if prev is None:
        os.environ.pop("GAMEPLAY_V2_ENABLED", None)
    else:
        os.environ["GAMEPLAY_V2_ENABLED"] = prev
    get_settings.cache_clear()
    metrics.reset_counters()


@pytest_asyncio.fixture
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded(client: AsyncClient):
    async with TestSession() as db:
        for s in SKILLS:
            db.add(Skill(**s))
        await db.flush()

        for p in PUZZLES:
            db.add(Puzzle(**p))
        await db.flush()

        for v in VARIANTS:
            db.add(
                PuzzleVariant(
                    id=v["id"],
                    puzzle_id=v["puzzle_id"],
                    difficulty_tier=v["difficulty_tier"],
                    prompt_text=v["prompt_text"],
                    correct_answers=v["correct_answers"],
                    audio_url=v.get("audio_url"),
                    time_limit_sec=v.get("time_limit_sec"),
                    metadata_=v.get("metadata", {}),
                )
            )

        for room in ROOM_TEMPLATES:
            db.add(RoomTemplate(room_id=room["room_id"], payload=room["payload"]))

        await db.commit()

    return client


async def _create_v2_session(client: AsyncClient) -> str:
    res = await client.post(
        "/api/sessions",
        json={"display_name": "metrics-user", "condition": "adaptive", "mode": "gameplay_v2"},
    )
    assert res.status_code == 200
    return res.json()["data"]["session_id"]


async def _get_version(client: AsyncClient, session_id: str) -> int:
    res = await client.get(f"/api/sessions/{session_id}/game-state")
    assert res.status_code == 200
    return res.json()["data"]["game_state"]["game_state_version"]


@pytest.mark.asyncio
async def test_trace_truncated_metric_increments_when_over_20_events(seeded: AsyncClient) -> None:
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    trace_events = [
        {"event_type": "hotspot_clicked", "hotspot_id": f"hs_{i}", "elapsed_ms": i}
        for i in range(25)
    ]

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
            "interaction_trace": {
                "version": 1,
                "type": "interaction_trace",
                "trace": trace_events,
                "response_time_ms": 1000,
            },
        },
    )
    assert res.status_code == 200
    assert metrics.get_counter("telemetry.trace.truncated") >= 1


@pytest.mark.asyncio
async def test_trace_too_large_metric_increments_for_oversized_event(seeded: AsyncClient) -> None:
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    huge_hotspot = "h" * 12000
    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
            "interaction_trace": {
                "version": 1,
                "type": "interaction_trace",
                "trace": [
                    {
                        "event_type": "hotspot_clicked",
                        "hotspot_id": huge_hotspot,
                        "elapsed_ms": 10,
                    }
                ],
                "response_time_ms": 50,
            },
        },
    )
    assert res.status_code == 200
    assert metrics.get_counter("telemetry.trace.too_large") >= 1

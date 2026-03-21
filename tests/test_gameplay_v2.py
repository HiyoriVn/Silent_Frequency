from __future__ import annotations

import json
import os
import uuid
from pathlib import Path

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import select
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from backend.app.config import get_settings
from backend.app.db.database import Base, get_db
from backend.app.db.models import EventLog, Puzzle, PuzzleVariant, RoomTemplate, Skill
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
def reset_flag_env():
    prev = os.environ.get("GAMEPLAY_V2_ENABLED")
    os.environ["GAMEPLAY_V2_ENABLED"] = "true"
    get_settings.cache_clear()
    yield
    if prev is None:
        os.environ.pop("GAMEPLAY_V2_ENABLED", None)
    else:
        os.environ["GAMEPLAY_V2_ENABLED"] = prev
    get_settings.cache_clear()


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_client(client: AsyncClient):
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


async def _create_session(client: AsyncClient, *, mode: str) -> str:
    res = await client.post(
        "/api/sessions",
        json={"display_name": f"user-{mode}", "condition": "adaptive", "mode": mode},
    )
    assert res.status_code == 200
    body = res.json()
    return body["data"]["session_id"]


@pytest.mark.asyncio
async def test_gameplay_v2_flow_idempotency_and_stale_conflict(seeded_client: AsyncClient) -> None:
    session_id = await _create_session(seeded_client, mode="gameplay_v2")

    get_res = await seeded_client.get(f"/api/sessions/{session_id}/game-state")
    assert get_res.status_code == 200
    get_body = get_res.json()
    game_state = get_body["data"]["game_state"]
    initial_version = game_state["game_state_version"]

    fixture_path = Path("tests/fixtures/gameplay_v2_action_use_item.json")
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    payload["client_action_id"] = str(uuid.uuid4())
    payload["game_state_version"] = initial_version

    first_res = await seeded_client.post(
        f"/api/sessions/{session_id}/action",
        json=payload,
    )
    assert first_res.status_code == 200
    first_body = first_res.json()
    assert first_body["ok"] is True
    assert len(first_body["data"]["effects"]) >= 1

    second_res = await seeded_client.post(
        f"/api/sessions/{session_id}/action",
        json=payload,
    )
    assert second_res.status_code == 200
    assert second_res.json() == first_body

    stale_payload = dict(payload)
    stale_payload["client_action_id"] = str(uuid.uuid4())
    stale_payload["game_state_version"] = initial_version

    stale_res = await seeded_client.post(
        f"/api/sessions/{session_id}/action",
        json=stale_payload,
    )
    assert stale_res.status_code == 409
    stale_body = stale_res.json()
    assert stale_body["error"]["code"] == "STATE_MISMATCH"
    assert stale_body["data_snapshot"]["game_state_version"] > initial_version

    async with TestSession() as db:
        events_result = await db.execute(
            select(EventLog).where(EventLog.session_id == uuid.UUID(session_id))
        )
        events = events_result.scalars().all()
    assert any(e.event_type == "game_action" for e in events)


@pytest.mark.asyncio
async def test_mode_mismatch_returns_403(seeded_client: AsyncClient) -> None:
    session_id = await _create_session(seeded_client, mode="phase3")
    res = await seeded_client.get(f"/api/sessions/{session_id}/game-state")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "MODE_MISMATCH"


@pytest.mark.asyncio
async def test_mode_disabled_returns_403(seeded_client: AsyncClient) -> None:
    os.environ["GAMEPLAY_V2_ENABLED"] = "false"
    get_settings.cache_clear()

    session_id = await _create_session(seeded_client, mode="gameplay_v2")
    res = await seeded_client.get(f"/api/sessions/{session_id}/game-state")
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "MODE_DISABLED"

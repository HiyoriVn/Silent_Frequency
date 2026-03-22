from __future__ import annotations

import json
import os
import uuid

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

engine = create_async_engine(
    TEST_DB_URL,
    echo=False,
    json_serializer=json.dumps,
    json_deserializer=json.loads,
)
Session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with Session() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture(autouse=True)
def enable_v2_flag():
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
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded(client: AsyncClient):
    async with Session() as db:
        for skill in SKILLS:
            db.add(Skill(**skill))
        await db.flush()

        for puzzle in PUZZLES:
            db.add(Puzzle(**puzzle))
        await db.flush()

        for variant in VARIANTS:
            db.add(
                PuzzleVariant(
                    id=variant["id"],
                    puzzle_id=variant["puzzle_id"],
                    difficulty_tier=variant["difficulty_tier"],
                    prompt_text=variant["prompt_text"],
                    correct_answers=variant["correct_answers"],
                    audio_url=variant.get("audio_url"),
                    time_limit_sec=variant.get("time_limit_sec"),
                    metadata_=variant.get("metadata", {}),
                )
            )

        for room in ROOM_TEMPLATES:
            db.add(RoomTemplate(room_id=room["room_id"], payload=room["payload"]))

        await db.commit()

    return client


@pytest.mark.asyncio
async def test_game_action_telemetry_exists_on_action(seeded: AsyncClient) -> None:
    create_res = await seeded.post(
        "/api/sessions",
        json={"display_name": "telemetry-user", "condition": "adaptive", "mode": "gameplay_v2"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["data"]["session_id"]

    state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert state_res.status_code == 200
    version = state_res.json()["data"]["game_state"]["game_state_version"]

    action_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert action_res.status_code == 200

    async with Session() as db:
        result = await db.execute(
            select(EventLog)
            .where(EventLog.event_type == "game_action")
            .order_by(EventLog.id.desc())
            .limit(1)
        )
        event = result.scalar_one_or_none()
        assert event is not None
        assert event.payload.get("type") == "game_action"
        assert event.payload.get("target_id") == "note"
        for effect in event.payload.get("resulting_effects", []):
            assert sorted(effect.keys()) == ["target_id", "type"]

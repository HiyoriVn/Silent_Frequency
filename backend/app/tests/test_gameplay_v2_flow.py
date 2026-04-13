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
    async with TestSession() as db:
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
async def test_v2_data_driven_resolver_flow(seeded: AsyncClient) -> None:
    create_res = await seeded.post(
        "/api/sessions",
        json={"display_name": "v2-user", "condition": "adaptive", "mode": "gameplay_v2"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["data"]["session_id"]

    state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert state_res.status_code == 200
    version = state_res.json()["data"]["game_state"]["game_state_version"]

    take_item_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "take_item",
            "target_id": "drawer",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert take_item_res.status_code == 200
    take_body = take_item_res.json()
    assert take_body["data"]["effects"][0]["type"] == "add_item"

    use_item_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "use_item",
            "target_id": "old_radio",
            "item_id": "bent_key",
            "game_state_version": take_body["meta"]["game_state_version"],
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert use_item_res.status_code == 200
    use_body = use_item_res.json()
    assert use_body["data"]["effects"][0]["type"] == "unlock"
    assert use_body["data"]["effects"][1]["type"] == "open_puzzle"

    inspect_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": use_body["meta"]["game_state_version"],
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert inspect_res.status_code == 200
    inspect_body = inspect_res.json()
    assert inspect_body["data"]["effects"][0]["type"] == "show_dialogue"
    assert "dialogue_text" in inspect_body["data"]["effects"][0]

    async with TestSession() as db:
        events_result = await db.execute(select(EventLog))
        events = events_result.scalars().all()
    assert len(events) >= 3


@pytest.mark.asyncio
async def test_v2_warm_start_adaptive_state_maps_self_assessed_level(
    seeded: AsyncClient,
) -> None:
    expected_by_level = {
        "beginner": "low",
        "elementary": "low",
        "intermediate": "mid",
        "upper_intermediate": "high",
    }

    for level, expected_tier in expected_by_level.items():
        create_res = await seeded.post(
            "/api/sessions",
            json={
                "display_name": f"warm-start-{level}",
                "condition": "adaptive",
                "mode": "gameplay_v2",
                "self_assessed_level": level,
            },
        )
        assert create_res.status_code == 200
        session_id = create_res.json()["data"]["session_id"]

        state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
        assert state_res.status_code == 200
        game_state = state_res.json()["data"]["game_state"]
        adaptive_state = game_state.get("adaptive_state")
        adaptive_output = game_state.get("adaptive_output")

        assert isinstance(adaptive_state, dict)
        assert isinstance(adaptive_output, dict)
        assert adaptive_output["difficulty_tier"] == expected_tier
        assert adaptive_output["warm_start_source"] == "self_assessed_level"
        assert adaptive_state["difficulty_tier"] == expected_tier
        assert adaptive_state["warm_start_source"] == "self_assessed_level"
        assert game_state["flags"]["self_assessed_level"] == level


@pytest.mark.asyncio
async def test_v2_warm_start_adaptive_state_defaults_to_mid_without_self_assessment(
    seeded: AsyncClient,
) -> None:
    create_res = await seeded.post(
        "/api/sessions",
        json={
            "display_name": "warm-start-default",
            "condition": "adaptive",
            "mode": "gameplay_v2",
        },
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["data"]["session_id"]

    state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert state_res.status_code == 200
    game_state = state_res.json()["data"]["game_state"]
    adaptive_state = game_state.get("adaptive_state")
    adaptive_output = game_state.get("adaptive_output")

    assert isinstance(adaptive_state, dict)
    assert isinstance(adaptive_output, dict)
    assert adaptive_output["difficulty_tier"] == "mid"
    assert adaptive_output["warm_start_source"] == "default"
    assert adaptive_state["difficulty_tier"] == "mid"
    assert adaptive_state["warm_start_source"] == "default"

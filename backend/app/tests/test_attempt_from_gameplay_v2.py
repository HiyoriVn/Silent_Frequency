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
from backend.app.db.models import Attempt, EventLog, Puzzle, PuzzleVariant, RoomTemplate, Skill
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
async def test_attempt_from_gameplay_v2_flow_persists_source_metadata(seeded: AsyncClient) -> None:
    create_res = await seeded.post(
        "/api/sessions",
        json={"display_name": "v2-attempt", "condition": "adaptive", "mode": "gameplay_v2"},
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
    use_item_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "use_item",
            "target_id": "old_radio",
            "item_id": "bent_key",
            "game_state_version": take_item_res.json()["meta"]["game_state_version"],
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert use_item_res.status_code == 200
    assert any(e["type"] == "open_puzzle" for e in use_item_res.json()["data"]["effects"])

    next_puzzle_res = await seeded.get(f"/api/sessions/{session_id}/next-puzzle")
    assert next_puzzle_res.status_code == 200
    variant_id = next_puzzle_res.json()["data"]["variant_id"]

    submit_res = await seeded.post(
        f"/api/sessions/{session_id}/attempts",
        json={
            "variant_id": variant_id,
            "answer": "test",
            "response_time_ms": 1234,
            "hint_count_used": 1,
            "game_state_version": use_item_res.json()["meta"]["game_state_version"],
            "interaction_trace": {
                "version": 1,
                "type": "interaction_trace",
                "puzzle_id": "p1",
                "variant_id": variant_id,
                "trace": [
                    {"event_type": "hint_opened", "hint_id": "hint_1", "elapsed_ms": 220}
                ],
                "response_time_ms": 1234,
            },
            "metadata": {"source": "gameplay_v2"},
        },
    )
    assert submit_res.status_code == 200

    async with Session() as db:
        attempt_result = await db.execute(
            select(Attempt).where(Attempt.session_id == uuid.UUID(session_id), Attempt.variant_id == variant_id)
        )
        attempt = attempt_result.scalar_one_or_none()
        assert attempt is not None

        event_result = await db.execute(
            select(EventLog)
            .where(EventLog.session_id == uuid.UUID(session_id), EventLog.event_type == "attempt_submitted")
            .order_by(EventLog.id.desc())
            .limit(1)
        )
        event = event_result.scalar_one_or_none()
        assert event is not None
        assert event.payload.get("metadata", {}).get("source") == "gameplay_v2"


@pytest.mark.asyncio
async def test_warning_sign_attempt_evaluates_by_canonical_puzzle_id(seeded: AsyncClient) -> None:
    create_res = await seeded.post(
        "/api/sessions",
        json={"display_name": "v2-warning-sign", "condition": "adaptive", "mode": "gameplay_v2"},
    )
    assert create_res.status_code == 200
    session_id = create_res.json()["data"]["session_id"]

    state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert state_res.status_code == 200
    version = state_res.json()["data"]["game_state"]["game_state_version"]

    trigger_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "warning_sign",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert trigger_res.status_code == 200
    assert any(e["type"] == "open_puzzle" for e in trigger_res.json()["data"]["effects"])

    wrong_res = await seeded.post(
        f"/api/sessions/{session_id}/attempts",
        json={
            "puzzle_id": "p_warning_sign_translate",
            "variant_id": "p_warning_sign_translate__fallback",
            "answer": "totally wrong answer",
            "response_time_ms": 900,
            "hint_count_used": 0,
            "metadata": {"source": "gameplay_v2"},
        },
    )
    assert wrong_res.status_code == 200
    wrong_body = wrong_res.json()["data"]
    assert wrong_body["puzzle_id"] == "p_warning_sign_translate"
    assert wrong_body["is_correct"] is False

    wrong_state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert wrong_state_res.status_code == 200
    wrong_state = wrong_state_res.json()["data"]["game_state"]
    wrong_flags = wrong_state.get("flags", {})
    assert wrong_flags.get("room404_exit_unlocked") is False
    assert wrong_flags.get("first_language_interaction_done") is False

    correct_res = await seeded.post(
        f"/api/sessions/{session_id}/attempts",
        json={
            "puzzle_id": "p_warning_sign_translate",
            "variant_id": "p_warning_sign_translate__fallback",
            "answer": "authorized personnel only",
            "response_time_ms": 950,
            "hint_count_used": 0,
            "metadata": {"source": "gameplay_v2"},
        },
    )
    assert correct_res.status_code == 200
    correct_body = correct_res.json()["data"]
    assert correct_body["puzzle_id"] == "p_warning_sign_translate"
    assert correct_body["is_correct"] is True

    solved_state_res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert solved_state_res.status_code == 200
    solved_state = solved_state_res.json()["data"]["game_state"]
    solved_flags = solved_state.get("flags", {})
    assert solved_flags.get("first_language_interaction_done") is True
    assert solved_flags.get("room404_exit_unlocked") is True
    assert "p_warning_sign_translate" not in (solved_state.get("active_puzzles") or [])

    main_door_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "navigation",
            "target_id": "main_door",
            "game_state_version": solved_state["game_state_version"],
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert main_door_res.status_code == 200
    dialogues = [
        e.get("dialogue_id")
        for e in main_door_res.json()["data"]["effects"]
        if e.get("type") == "show_dialogue"
    ]
    assert "room404_door_unlocked" in dialogues

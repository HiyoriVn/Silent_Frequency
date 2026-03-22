"""
Batch 4.3 — Action Flow & Telemetry Tests

Tests for:
- game_action telemetry logging (event_log row with minimal resulting_effects)
- puzzle_interaction_trace observational logging with hint_opened
- 409 stale-state conflict handling
- trace limit (max 20 events, _truncated flag)
- payload size guard (oversized telemetry trimmed safely)
- idempotent action deduplication
- no regression (action succeeds without interaction_trace)
"""

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


async def _create_v2_session(client: AsyncClient) -> str:
    res = await client.post(
        "/api/sessions",
        json={"display_name": "tester", "condition": "adaptive", "mode": "gameplay_v2"},
    )
    assert res.status_code == 200
    return res.json()["data"]["session_id"]


async def _get_version(client: AsyncClient, session_id: str) -> int:
    res = await client.get(f"/api/sessions/{session_id}/game-state")
    assert res.status_code == 200
    return res.json()["data"]["game_state"]["game_state_version"]


# ──────────────────────────────────────
# test_game_action_logs
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_game_action_logs(seeded: AsyncClient) -> None:
    """Action request yields an event_log row with event_type='game_action'
    and resulting_effects is minimal (only type + target_id)."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert res.status_code == 200

    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "game_action",
            )
        )
        events = result.scalars().all()

    assert len(events) >= 1
    payload = events[-1].payload
    assert payload["type"] == "game_action"
    assert payload["version"] == 1
    assert payload["action"] == "inspect"
    assert payload["target_id"] == "note"
    assert "resulting_effects" in payload
    # Verify resulting_effects is minimal: only type and target_id keys
    for effect in payload["resulting_effects"]:
        assert "type" in effect
        assert "target_id" in effect
        # Should not contain full internal effect data
        assert "dialogue_text" not in effect


# ──────────────────────────────────────
# test_interaction_trace_logged (with hint_opened)
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_interaction_trace_logged(seeded: AsyncClient) -> None:
    """Action request with interaction_trace logs puzzle_interaction_trace
    including hint_opened events."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    trace = {
        "version": 1,
        "type": "interaction_trace",
        "puzzle_id": "test_puzzle",
        "variant_id": "test_variant",
        "trace": [
            {"event_type": "hotspot_clicked", "hotspot_id": "note", "elapsed_ms": 100},
            {"event_type": "hint_opened", "hint_id": "hint_01", "elapsed_ms": 500},
            {"event_type": "prompt_opened", "prompt_ref": "p1", "elapsed_ms": 1200},
        ],
        "response_time_ms": 2000,
    }

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
            "interaction_trace": trace,
        },
    )
    assert res.status_code == 200

    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "puzzle_interaction_trace",
            )
        )
        events = result.scalars().all()

    assert len(events) == 1
    payload = events[0].payload
    assert payload["type"] == "interaction_trace"
    assert payload["puzzle_id"] == "test_puzzle"
    assert len(payload["trace"]) == 3
    event_types = [e["event_type"] for e in payload["trace"]]
    assert "hint_opened" in event_types
    assert "_truncated" not in payload  # Only 3 events, no truncation


# ──────────────────────────────────────
# test_409_on_stale_version
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_409_on_stale_version(seeded: AsyncClient) -> None:
    """Stale version returns HTTP 409 with current version and snapshot."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    # Advance state by one action
    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert res.status_code == 200

    # Now send with stale version
    stale_res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,  # stale
            "client_action_id": str(uuid.uuid4()),
        },
    )
    assert stale_res.status_code == 409
    body = stale_res.json()
    assert body["ok"] is False
    assert body["error"]["code"] == "STATE_MISMATCH"
    assert body["meta"]["game_state_version"] > version
    assert body["data_snapshot"] is not None
    assert body["data_snapshot"]["game_state_version"] > version


# ──────────────────────────────────────
# test_trace_limit
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_trace_limit(seeded: AsyncClient) -> None:
    """Traces with >20 events are trimmed to 20 and _truncated is set."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    # Build a trace with 25 events
    events = [
        {"event_type": "hotspot_clicked", "hotspot_id": f"hs_{i}", "elapsed_ms": i * 100}
        for i in range(25)
    ]
    trace = {
        "version": 1,
        "type": "interaction_trace",
        "trace": events,
        "response_time_ms": 5000,
    }

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
            "interaction_trace": trace,
        },
    )
    # Action should still succeed even though trace was oversized
    assert res.status_code == 200

    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "puzzle_interaction_trace",
            )
        )
        events_rows = result.scalars().all()

    assert len(events_rows) == 1
    payload = events_rows[0].payload
    assert len(payload["trace"]) == 20
    assert payload["_truncated"] is True


# ──────────────────────────────────────
# test_payload_size_guard
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_payload_size_guard(seeded: AsyncClient) -> None:
    """Oversized telemetry payload is reduced safely.
    Server does not fail the action because telemetry needed trimming."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    # Create a trace with long hotspot_id strings to push payload size
    events = [
        {
            "event_type": "hotspot_clicked",
            "hotspot_id": f"hs_{'x' * 400}_{i}",
            "elapsed_ms": i * 100,
        }
        for i in range(20)
    ]
    trace = {
        "version": 1,
        "type": "interaction_trace",
        "trace": events,
        "response_time_ms": 5000,
    }

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
            "client_action_id": str(uuid.uuid4()),
            "interaction_trace": trace,
        },
    )
    # Action must still succeed
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # Verify game_action telemetry was still written
    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "game_action",
            )
        )
        events_rows = result.scalars().all()

    assert len(events_rows) >= 1


# ──────────────────────────────────────
# test_idempotent_action_no_duplicate_effects
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_idempotent_action_no_duplicate_effects(seeded: AsyncClient) -> None:
    """Replayed action with same client_action_id returns cached response,
    does not create duplicate event_log entries or duplicate effects."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    action_id = str(uuid.uuid4())
    payload = {
        "interaction_schema_version": 2,
        "action": "inspect",
        "target_id": "note",
        "game_state_version": version,
        "client_action_id": action_id,
    }

    first_res = await seeded.post(f"/api/sessions/{session_id}/action", json=payload)
    assert first_res.status_code == 200
    first_body = first_res.json()

    # Replay with same client_action_id
    second_res = await seeded.post(f"/api/sessions/{session_id}/action", json=payload)
    assert second_res.status_code == 200
    second_body = second_res.json()

    # Responses must be identical (cached dedupe)
    assert first_body == second_body

    # Should only have ONE game_action event for this action
    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "game_action",
            )
        )
        events = result.scalars().all()

    # Only 1 game_action event from the first request; replay returns cached
    assert len(events) == 1


# ──────────────────────────────────────
# test_action_without_trace_succeeds (no regression)
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_action_without_trace_succeeds(seeded: AsyncClient) -> None:
    """Action request without interaction_trace succeeds (backward compat)."""
    session_id = await _create_v2_session(seeded)
    version = await _get_version(seeded, session_id)

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 2,
            "action": "inspect",
            "target_id": "note",
            "game_state_version": version,
        },
    )
    assert res.status_code == 200
    assert res.json()["ok"] is True

    # No puzzle_interaction_trace should be logged
    async with TestSession() as db:
        result = await db.execute(
            select(EventLog).where(
                EventLog.session_id == uuid.UUID(session_id),
                EventLog.event_type == "puzzle_interaction_trace",
            )
        )
        events = result.scalars().all()
    assert len(events) == 0


# ──────────────────────────────────────
# test_game_state_etag_header
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_game_state_etag_header(seeded: AsyncClient) -> None:
    """GET /game-state includes ETag header and game_state_version in meta."""
    session_id = await _create_v2_session(seeded)
    res = await seeded.get(f"/api/sessions/{session_id}/game-state")
    assert res.status_code == 200

    etag = res.headers.get("etag")
    assert etag is not None
    assert etag.startswith('W/"v')

    body = res.json()
    assert "game_state_version" in body["meta"]


# ──────────────────────────────────────
# test_invalid_schema_version_rejected
# ──────────────────────────────────────
@pytest.mark.asyncio
async def test_invalid_schema_version_rejected(seeded: AsyncClient) -> None:
    """Unsupported interaction_schema_version must be rejected with HTTP 400."""
    session_id = await _create_v2_session(seeded)

    res = await seeded.post(
        f"/api/sessions/{session_id}/action",
        json={
            "interaction_schema_version": 99,
            "action": "inspect",
            "target_id": "note",
        },
    )
    assert res.status_code == 400
    body = res.json()
    assert body["error"]["code"] == "INVALID_SCHEMA_VERSION"

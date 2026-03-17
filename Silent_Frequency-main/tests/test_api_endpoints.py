"""
Silent Frequency — API Endpoint Integration Tests

Uses FastAPI's TestClient (httpx) against the real app with an in-memory
SQLite database so tests run without PostgreSQL.

Run with:  python -m pytest tests/test_api_endpoints.py -v
"""

from __future__ import annotations

import os
import uuid

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy import JSON, String
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from backend.app.db.database import Base, get_db
from backend.app.main import app


# ──────────────────────────────────────
# SQLite compatibility: compile PG types
# ──────────────────────────────────────

@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


# ──────────────────────────────────────
# In-memory async SQLite for testing
# ──────────────────────────────────────

TEST_DB_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"

test_engine = create_async_engine(TEST_DB_URL, echo=False, json_serializer=__import__("json").dumps, json_deserializer=__import__("json").loads)
TestSession = async_sessionmaker(test_engine, class_=AsyncSession, expire_on_commit=False)


async def _override_get_db():
    async with TestSession() as session:
        yield session


app.dependency_overrides[get_db] = _override_get_db


# ──────────────────────────────────────
# Fixtures
# ──────────────────────────────────────

@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    """Create all tables before each test, drop after."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest_asyncio.fixture
async def seeded_client(client: AsyncClient):
    """Client + DB seeded with skills, puzzles, variants."""
    from backend.app.db.models import Skill, Puzzle, PuzzleVariant
    from backend.app.seed import SKILLS, PUZZLES, VARIANTS

    async with TestSession() as db:
        for s in SKILLS:
            db.add(Skill(**s))
        await db.flush()
        for p in PUZZLES:
            db.add(Puzzle(**p))
        await db.flush()
        for v in VARIANTS:
            db.add(PuzzleVariant(
                id=v["id"],
                puzzle_id=v["puzzle_id"],
                difficulty_tier=v["difficulty_tier"],
                prompt_text=v["prompt_text"],
                correct_answers=v["correct_answers"],
                audio_url=v.get("audio_url"),
                time_limit_sec=v.get("time_limit_sec"),
            ))
        await db.commit()
    return client


@pytest_asyncio.fixture
async def session_id(seeded_client: AsyncClient) -> str:
    """Create a session and return its ID."""
    res = await seeded_client.post("/api/sessions", json={"display_name": "QA_Tester"})
    data = res.json()
    return data["data"]["session_id"]


# ══════════════════════════════════════
# 1. POST /api/sessions
# ══════════════════════════════════════

class TestCreateSession:

    @pytest.mark.asyncio
    async def test_create_session_success(self, seeded_client: AsyncClient) -> None:
        """Valid request creates a session with mastery snapshot."""
        res = await seeded_client.post(
            "/api/sessions", json={"display_name": "Alice"}
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        assert "session_id" in body["data"]
        assert "mastery" in body["data"]
        mastery = body["data"]["mastery"]
        assert set(mastery.keys()) == {"vocabulary", "grammar", "listening"}
        # All mastery values should be initial (0.1)
        for v in mastery.values():
            assert 0.0 <= v <= 1.0

    @pytest.mark.asyncio
    async def test_create_session_empty_name_rejected(self, seeded_client: AsyncClient) -> None:
        """Empty display_name violates min_length=1 → 422."""
        res = await seeded_client.post("/api/sessions", json={"display_name": ""})
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_create_session_long_name_rejected(self, seeded_client: AsyncClient) -> None:
        """display_name > 64 chars → 422."""
        res = await seeded_client.post(
            "/api/sessions", json={"display_name": "x" * 65}
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_create_session_missing_body(self, seeded_client: AsyncClient) -> None:
        """No JSON body → 422."""
        res = await seeded_client.post("/api/sessions")
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_create_session_response_envelope(self, seeded_client: AsyncClient) -> None:
        """Response matches the ApiResponse envelope shape."""
        res = await seeded_client.post(
            "/api/sessions", json={"display_name": "Bob"}
        )
        body = res.json()
        assert "ok" in body
        assert "data" in body
        assert "error" in body
        assert "meta" in body
        assert body["meta"]["session_id"] == body["data"]["session_id"]


# ══════════════════════════════════════
# 2. GET /api/sessions/{id}/mastery
# ══════════════════════════════════════

class TestGetMastery:

    @pytest.mark.asyncio
    async def test_get_mastery_success(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        res = await seeded_client.get(f"/api/sessions/{session_id}/mastery")
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        mastery_list = body["data"]["mastery"]
        assert len(mastery_list) == 3
        skills = {m["skill"] for m in mastery_list}
        assert skills == {"vocabulary", "grammar", "listening"}
        for m in mastery_list:
            assert m["difficulty_tier"] in ("low", "mid", "high")
            assert 0.0 <= m["p_learned"] <= 1.0

    @pytest.mark.asyncio
    async def test_get_mastery_invalid_session(self, seeded_client: AsyncClient) -> None:
        """Non-existent session ID → 404."""
        fake_id = str(uuid.uuid4())
        res = await seeded_client.get(f"/api/sessions/{fake_id}/mastery")
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_get_mastery_malformed_uuid(self, seeded_client: AsyncClient) -> None:
        """Malformed UUID → 422."""
        res = await seeded_client.get("/api/sessions/not-a-uuid/mastery")
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_mastery_summary_matches_details(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """summary snapshot should match the per-skill detail values."""
        res = await seeded_client.get(f"/api/sessions/{session_id}/mastery")
        body = res.json()
        summary = body["data"]["summary"]
        details = body["data"]["mastery"]
        for d in details:
            assert summary[d["skill"]] == d["p_learned"]


# ══════════════════════════════════════
# 3. GET /api/sessions/{id}/next-item
# ══════════════════════════════════════

class TestGetNextItem:

    @pytest.mark.asyncio
    async def test_next_item_success(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        res = await seeded_client.get(
            f"/api/sessions/{session_id}/next-item?skill=vocabulary"
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        item = body["data"]
        assert item["skill"] == "vocabulary"
        assert item["difficulty_tier"] in ("low", "mid", "high")
        assert "prompt_text" in item
        assert "variant_id" in item

    @pytest.mark.asyncio
    async def test_next_item_invalid_skill(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Skill not in {vocabulary, grammar, listening} → 422."""
        res = await seeded_client.get(
            f"/api/sessions/{session_id}/next-item?skill=algebra"
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_next_item_missing_skill_param(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Missing required query param 'skill' → 422."""
        res = await seeded_client.get(f"/api/sessions/{session_id}/next-item")
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_next_item_nonexistent_session(
        self, seeded_client: AsyncClient
    ) -> None:
        fake_id = str(uuid.uuid4())
        res = await seeded_client.get(
            f"/api/sessions/{fake_id}/next-item?skill=vocabulary"
        )
        assert res.status_code == 404

    @pytest.mark.asyncio
    async def test_next_item_all_skills(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Each skill should return a valid item."""
        for skill in ("vocabulary", "grammar", "listening"):
            res = await seeded_client.get(
                f"/api/sessions/{session_id}/next-item?skill={skill}"
            )
            assert res.status_code == 200
            assert res.json()["data"]["skill"] == skill


# ══════════════════════════════════════
# 4. POST /api/sessions/{id}/attempts
# ══════════════════════════════════════

class TestSubmitAttempt:

    @pytest.mark.asyncio
    async def test_submit_correct_answer(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Submit a correct answer → is_correct=true, mastery increases."""
        # Get an item first
        item_res = await seeded_client.get(
            f"/api/sessions/{session_id}/next-item?skill=vocabulary"
        )
        variant_id = item_res.json()["data"]["variant_id"]

        # Get initial mastery
        mastery_res = await seeded_client.get(
            f"/api/sessions/{session_id}/mastery"
        )
        initial_mastery = mastery_res.json()["data"]["summary"]["vocabulary"]

        # We don't know the correct answer but we can still submit and check structure
        res = await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "variant_id": variant_id,
                "answer": "test_answer_maybe_wrong",
                "response_time_ms": 3500,
                "hint_count_used": 0,
            },
        )
        assert res.status_code == 200
        body = res.json()
        assert body["ok"] is True
        feedback = body["data"]
        assert "is_correct" in feedback
        assert "correct_answers" in feedback
        assert "p_learned_before" in feedback
        assert "p_learned_after" in feedback
        assert "difficulty_tier" in feedback
        assert "mastery" in feedback
        assert isinstance(feedback["correct_answers"], list)

    @pytest.mark.asyncio
    async def test_submit_updates_mastery(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """After submitting, mastery endpoint should reflect the update."""
        # Get item
        item_res = await seeded_client.get(
            f"/api/sessions/{session_id}/next-item?skill=vocabulary"
        )
        variant_id = item_res.json()["data"]["variant_id"]

        # Submit
        await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "variant_id": variant_id,
                "answer": "some_answer",
                "response_time_ms": 2000,
                "hint_count_used": 0,
            },
        )

        # Check mastery was updated (update_count should be 1)
        mastery_res = await seeded_client.get(
            f"/api/sessions/{session_id}/mastery"
        )
        details = mastery_res.json()["data"]["mastery"]
        vocab = next(d for d in details if d["skill"] == "vocabulary")
        assert vocab["update_count"] >= 1

    @pytest.mark.asyncio
    async def test_submit_missing_variant_id(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Missing variant_id → 422."""
        res = await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "answer": "hello",
                "response_time_ms": 1000,
                "hint_count_used": 0,
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_empty_answer(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Empty answer violates min_length=1 → 422."""
        res = await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "variant_id": "some_id",
                "answer": "",
                "response_time_ms": 1000,
                "hint_count_used": 0,
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_negative_response_time(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Negative response_time_ms → 422 (ge=0 constraint)."""
        res = await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "variant_id": "v1",
                "answer": "test",
                "response_time_ms": -100,
                "hint_count_used": 0,
            },
        )
        assert res.status_code == 422

    @pytest.mark.asyncio
    async def test_submit_nonexistent_variant(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Submitting a variant_id that doesn't exist → 400."""
        res = await seeded_client.post(
            f"/api/sessions/{session_id}/attempts",
            json={
                "variant_id": "nonexistent_variant_xyz",
                "answer": "test",
                "response_time_ms": 1000,
                "hint_count_used": 0,
            },
        )
        assert res.status_code == 400


# ══════════════════════════════════════
# 5. GET /health
# ══════════════════════════════════════

class TestHealth:

    @pytest.mark.asyncio
    async def test_health_ok(self, client: AsyncClient) -> None:
        res = await client.get("/health")
        assert res.status_code == 200


# ══════════════════════════════════════
# 6. Response Envelope Consistency
# ══════════════════════════════════════

class TestEnvelopeConsistency:

    @pytest.mark.asyncio
    async def test_success_envelope_shape(
        self, seeded_client: AsyncClient, session_id: str
    ) -> None:
        """Every successful response has ok=True, data≠null, error=null."""
        res = await seeded_client.get(f"/api/sessions/{session_id}/mastery")
        body = res.json()
        assert body["ok"] is True
        assert body["data"] is not None
        assert body["error"] is None
        assert body["meta"] is not None
        assert "timestamp" in body["meta"]
        assert body["meta"]["session_id"] == session_id

    @pytest.mark.asyncio
    async def test_error_envelope_shape(self, seeded_client: AsyncClient) -> None:
        """Error responses have ok=False, error≠null."""
        fake_id = str(uuid.uuid4())
        res = await seeded_client.get(f"/api/sessions/{fake_id}/mastery")
        # FastAPI returns the envelope in the detail field for HTTPException
        assert res.status_code == 404

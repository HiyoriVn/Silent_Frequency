from __future__ import annotations

import json

import pytest
import pytest_asyncio
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles

from backend.app.db.database import Base
from backend.app.db.models import GameSession, GameState, Player


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


@pytest_asyncio.fixture(autouse=True)
async def setup_db():
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.mark.asyncio
async def test_game_session_mode_is_immutable_once_persisted() -> None:
    async with TestSession() as db:
        player = Player(display_name="p1", session_token="tok-1")
        db.add(player)
        await db.flush()

        session = GameSession(player_id=player.id, mode="gameplay_v2")
        db.add(session)
        await db.flush()

        with pytest.raises(ValueError, match="immutable"):
            session.mode = "phase3"


@pytest.mark.asyncio
async def test_game_state_version_defaults_to_zero() -> None:
    async with TestSession() as db:
        player = Player(display_name="p2", session_token="tok-2")
        db.add(player)
        await db.flush()

        session = GameSession(player_id=player.id, mode="phase3")
        db.add(session)
        await db.flush()

        state = GameState(session_id=session.id)
        db.add(state)
        await db.flush()

        assert state.game_state_version == 0

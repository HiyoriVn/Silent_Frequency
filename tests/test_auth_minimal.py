"""
Minimal auth integration tests for Batch 1.1.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.dialects.postgresql import JSONB, UUID as PG_UUID

from backend.app.db.database import Base, get_db
from backend.app.main import app


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


@compiles(PG_UUID, "sqlite")
def _compile_uuid_sqlite(type_, compiler, **kw):
    return "CHAR(32)"


TEST_DB_URL = "sqlite+aiosqlite:///file::memory:?cache=shared&uri=true"
test_engine = create_async_engine(TEST_DB_URL, echo=False)
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


@pytest_asyncio.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient) -> None:
    res = await client.post(
        "/api/auth/register",
        json={"username": "tester1", "password": "password123"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["data"]["username"] == "tester1"
    assert isinstance(body["data"]["auth_token"], str)
    assert body["data"]["auth_token"]


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "tester2", "password": "password123"},
    )

    res = await client.post(
        "/api/auth/login",
        json={"username": "tester2", "password": "password123"},
    )

    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["data"]["username"] == "tester2"


@pytest.mark.asyncio
async def test_login_invalid_password_rejected(client: AsyncClient) -> None:
    await client.post(
        "/api/auth/register",
        json={"username": "tester3", "password": "password123"},
    )

    res = await client.post(
        "/api/auth/login",
        json={"username": "tester3", "password": "wrong-password"},
    )

    assert res.status_code == 401
    body = res.json()
    assert body["detail"]["ok"] is False
    assert body["detail"]["error"]["code"] == "INVALID_CREDENTIALS"


@pytest.mark.asyncio
async def test_logout_success(client: AsyncClient) -> None:
    register_res = await client.post(
        "/api/auth/register",
        json={"username": "tester4", "password": "password123"},
    )
    token = register_res.json()["data"]["auth_token"]

    logout_res = await client.post(
        "/api/auth/logout",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert logout_res.status_code == 200
    body = logout_res.json()
    assert body["ok"] is True
    assert body["data"]["logged_out"] is True

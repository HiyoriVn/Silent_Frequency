"""
Silent Frequency — FastAPI Application Entry Point

Wires together: config → DB → routes → lifespan.
Run with:  uvicorn backend.app.main:app --reload
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import get_settings
from .db.database import engine, Base
from .api.routes import router


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan:
      - On startup: create tables (dev convenience — use Alembic in prod).
      - On shutdown: dispose engine.
    """
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    await engine.dispose()


settings = get_settings()

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    lifespan=lifespan,
)

# CORS — allow the Next.js frontend during development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount all routes
app.include_router(router)


@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.app_version}

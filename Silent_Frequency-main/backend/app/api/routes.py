"""
Silent Frequency — API Routes

All game endpoints, mounted under /api.
Each route is thin: validate → delegate to service → wrap response.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..db.database import get_db
from ..services import session_service, mastery_service, puzzle_service
from .schemas import (
    ApiResponse,
    ApiMeta,
    ApiError,
    CreateSessionRequest,
    SessionCreated,
    MasterySnapshot,
    MasteryDetail,
    MasteryResponse,
    NextPuzzleResponse,
    SubmitAttemptRequest,
    AttemptFeedback,
)

router = APIRouter(prefix="/api")


# ──────────────────────────────────────
# Helper
# ──────────────────────────────────────
def _meta(session_id: uuid.UUID) -> ApiMeta:
    return ApiMeta(timestamp=datetime.now(timezone.utc), session_id=session_id)


def _error_response(code: str, message: str, status: int = 400) -> HTTPException:
    return HTTPException(
        status_code=status,
        detail=ApiResponse(
            ok=False,
            error=ApiError(code=code, message=message),
        ).model_dump(),
    )


# ──────────────────────────────────────
# POST /api/sessions
# ──────────────────────────────────────
@router.post("/sessions", response_model=ApiResponse)
async def create_session(
    body: CreateSessionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Create a new player + game session with initialised BKT state."""
    data = await session_service.create_session(
        db, body.display_name, body.condition
    )

    return ApiResponse(
        ok=True,
        data=SessionCreated(
            session_id=data["session_id"],
            player_id=data["player_id"],
            session_token=data["session_token"],
            condition=data["condition"],
            current_level_index=data["current_level_index"],
            mastery=MasterySnapshot(**data["mastery"]),
            current_room=data["current_room"],
        ),
        meta=_meta(data["session_id"]),
    )


# ──────────────────────────────────────
# GET /api/sessions/{id}/mastery
# ──────────────────────────────────────
@router.get("/sessions/{session_id}/mastery", response_model=ApiResponse)
async def get_mastery(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Return per-skill mastery + recommended difficulty tiers."""
    session = await session_service.get_session_or_none(db, session_id)
    if session is None:
        raise _error_response("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    rows = await mastery_service.get_mastery_for_session(db, session_id)
    snapshot = {r["skill"]: r["p_learned"] for r in rows}

    return ApiResponse(
        ok=True,
        data=MasteryResponse(
            session_id=session_id,
            mastery=[MasteryDetail(**r) for r in rows],
            summary=MasterySnapshot(**snapshot),
        ),
        meta=_meta(session_id),
    )


# ──────────────────────────────────────
# GET /api/sessions/{id}/next-puzzle
# ──────────────────────────────────────
@router.get("/sessions/{session_id}/next-puzzle", response_model=ApiResponse)
async def get_next_puzzle(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Select the next puzzle from backend-owned fixed progression."""
    session = await session_service.get_session_or_none(db, session_id)
    if session is None:
        raise _error_response("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    try:
        data = await puzzle_service.get_next_puzzle(db, session_id)
    except ValueError as e:
        raise _error_response("SELECTION_ERROR", str(e))

    return ApiResponse(
        ok=True,
        data=NextPuzzleResponse(**data),
        meta=_meta(session_id),
    )


# ──────────────────────────────────────
# POST /api/sessions/{id}/attempts
# ──────────────────────────────────────
@router.post("/sessions/{session_id}/attempts", response_model=ApiResponse)
async def submit_attempt(
    session_id: uuid.UUID,
    body: SubmitAttemptRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Submit a puzzle answer.

    Scores the answer, runs BKT update, logs the attempt,
    and returns feedback with updated mastery.
    """
    session = await session_service.get_session_or_none(db, session_id)
    if session is None:
        raise _error_response("SESSION_NOT_FOUND", f"Session {session_id} not found", 404)

    try:
        data = await puzzle_service.submit_attempt(
            db=db,
            session_id=session_id,
            variant_id=body.variant_id,
            player_answer=body.answer,
            response_time_ms=body.response_time_ms,
            hint_count_used=body.hint_count_used,
        )
    except ValueError as e:
        raise _error_response("ATTEMPT_ERROR", str(e))

    return ApiResponse(
        ok=True,
        data=AttemptFeedback(
            is_correct=data["is_correct"],
            correct_answers=data["correct_answers"],
            p_learned_before=data["p_learned_before"],
            p_learned_after=data["p_learned_after"],
            difficulty_tier=data["difficulty_tier"],
            current_level_index=data["current_level_index"],
            session_complete=data["session_complete"],
            mastery=MasterySnapshot(**data["mastery"]),
        ),
        meta=_meta(session_id),
    )

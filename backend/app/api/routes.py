"""
Silent Frequency — API Routes

All game endpoints, mounted under /api.
Each route is thin: validate → delegate to service → wrap response.
"""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from .. import metrics
from ..db.database import get_db
from ..db.models import EventLog, GameState, PuzzleVariant
from ..services import auth_service, session_service, mastery_service, puzzle_service, game_service
from .schemas import (
    ApiResponse,
    ApiMeta,
    ApiError,
    RegisterRequest,
    LoginRequest,
    AuthResponseData,
    LogoutResponseData,
    CreateSessionRequest,
    SessionCreated,
    MasterySnapshot,
    MasteryDetail,
    MasteryResponse,
    NextPuzzleResponse,
    SubmitAttemptRequest,
    AttemptFeedback,
    ActionRequest,
)

router = APIRouter(prefix="/api")
MAX_TRACE_EVENTS = 20
MAX_TRACE_EVENT_BYTES = 10_000


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


def _extract_bearer_token(authorization: str | None) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if not authorization.startswith(prefix):
        return None
    token = authorization[len(prefix):].strip()
    return token or None


def _sanitize_trace_events(
    events: list[dict[str, Any]] | None,
) -> tuple[list[dict[str, Any]] | None, bool]:
    if events is None:
        return None, False

    event_count_truncated = len(events) > MAX_TRACE_EVENTS
    trimmed: list[dict[str, Any]] = []
    oversized_trimmed = False

    for event in events[:MAX_TRACE_EVENTS]:
        serialized = json.dumps(event)
        if len(serialized) <= MAX_TRACE_EVENT_BYTES:
            trimmed.append(event)
            continue

        oversized_trimmed = True
        trimmed.append(
            {
                "event_type": event.get("event_type", "unknown"),
                "hotspot_id": event.get("hotspot_id"),
                "prompt_ref": event.get("prompt_ref"),
                "hint_id": event.get("hint_id"),
                "elapsed_ms": int(event.get("elapsed_ms", 0) or 0),
                "_oversized": True,
            }
        )

    truncated = event_count_truncated or oversized_trimmed
    if truncated:
        metrics.increment("telemetry.trace.truncated")
    if oversized_trimmed:
        metrics.increment("telemetry.trace.too_large")

    return trimmed, truncated


# ──────────────────────────────────────
# POST /api/auth/register
# ──────────────────────────────────────
@router.post("/auth/register", response_model=ApiResponse)
async def register(
    body: RegisterRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await auth_service.register_user(
            db,
            username=body.username,
            password=body.password,
            real_name=body.real_name,
        )
    except auth_service.AuthServiceError as exc:
        raise _error_response(exc.code, exc.message, exc.status_code)

    return ApiResponse(
        ok=True,
        data=AuthResponseData(**data),
        meta=None,
    )


# ──────────────────────────────────────
# POST /api/auth/login
# ──────────────────────────────────────
@router.post("/auth/login", response_model=ApiResponse)
async def login(
    body: LoginRequest,
    db: AsyncSession = Depends(get_db),
):
    try:
        data = await auth_service.login_user(
            db,
            username=body.username,
            password=body.password,
        )
    except auth_service.AuthServiceError as exc:
        raise _error_response(exc.code, exc.message, exc.status_code)

    return ApiResponse(
        ok=True,
        data=AuthResponseData(**data),
        meta=None,
    )


# ──────────────────────────────────────
# POST /api/auth/logout
# ──────────────────────────────────────
@router.post("/auth/logout", response_model=ApiResponse)
async def logout(
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
):
    auth_token = _extract_bearer_token(authorization)
    if auth_token is None:
        raise _error_response("INVALID_TOKEN", "Missing or invalid bearer token", 401)

    try:
        await auth_service.logout_user(db, auth_token)
    except auth_service.AuthServiceError as exc:
        raise _error_response(exc.code, exc.message, exc.status_code)

    return ApiResponse(
        ok=True,
        data=LogoutResponseData(logged_out=True),
        meta=None,
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
        db,
        body.display_name,
        body.condition,
        body.mode,
        body.self_assessed_level,
    )

    return ApiResponse(
        ok=True,
        data=SessionCreated(
            session_id=data["session_id"],
            player_id=data["player_id"],
            session_token=data["session_token"],
            condition=data["condition"],
            mode=data["mode"],
            self_assessed_level=data["self_assessed_level"],
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

    if data.get("variant_id"):
        variant_result = await db.execute(
            select(PuzzleVariant)
            .options(joinedload(PuzzleVariant.puzzle))
            .where(PuzzleVariant.id == data["variant_id"])
        )
        variant = variant_result.scalar_one_or_none()
        if variant is not None:
            metadata = variant.metadata_ or {}
            data["hints"] = list(metadata.get("hints") or [])
            data["max_hints_shown"] = metadata.get("max_hints_shown") or variant.puzzle.max_hints
            interaction = metadata.get("interaction") or {}
            prompts = interaction.get("prompts") if isinstance(interaction, dict) else None
            max_attempt_chars = None
            if isinstance(prompts, dict):
                for prompt in prompts.values():
                    if isinstance(prompt, dict) and prompt.get("max_attempt_chars") is not None:
                        max_attempt_chars = int(prompt["max_attempt_chars"])
                        break
            data["max_attempt_chars"] = max_attempt_chars

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

    if body.game_state_version is not None and session.mode == "gameplay_v2":
        state = await db.get(GameState, session_id)
        if state is not None and body.game_state_version != state.game_state_version:
            snapshot = await game_service.get_game_state(db, session_id)
            payload = {
                "ok": False,
                "data": None,
                "error": {"code": "STATE_MISMATCH", "message": "client state stale"},
                "meta": {
                    "interaction_schema_version": 2,
                    "game_state_version": state.game_state_version,
                },
                "data_snapshot": snapshot,
            }
            return JSONResponse(status_code=409, content=jsonable_encoder(payload))

    sanitized_trace: list[dict[str, Any]] | None = None
    trace_was_truncated = False
    if body.interaction_trace is not None:
        raw_events = [event.model_dump() for event in body.interaction_trace.trace]
        sanitized_trace, trace_was_truncated = _sanitize_trace_events(raw_events)

    try:
        data = await puzzle_service.submit_attempt(
            db=db,
            session_id=session_id,
            puzzle_id=body.puzzle_id,
            variant_id=body.variant_id,
            player_answer=body.answer,
            response_time_ms=body.response_time_ms,
            hint_count_used=body.hint_count_used,
            interaction_trace=sanitized_trace,
        )
    except ValueError as e:
        raise _error_response("ATTEMPT_ERROR", str(e))

    if body.metadata is not None or body.interaction_trace is not None:
        event_result = await db.execute(
            select(EventLog)
            .where(
                EventLog.session_id == session_id,
                EventLog.event_type == "attempt_submitted",
            )
            .order_by(EventLog.id.desc())
            .limit(1)
        )
        attempt_event = event_result.scalar_one_or_none()
        if attempt_event is not None and body.metadata is not None:
            payload = dict(attempt_event.payload)
            payload["metadata"] = body.metadata.model_dump()
            attempt_event.payload = payload

        if body.interaction_trace is not None:
            trace_result = await db.execute(
                select(EventLog)
                .where(
                    EventLog.session_id == session_id,
                    EventLog.event_type == "puzzle_interaction_trace",
                )
                .order_by(EventLog.id.desc())
                .limit(1)
            )
            trace_event = trace_result.scalar_one_or_none()
            if trace_event is not None:
                trace_payload = dict(trace_event.payload)
                trace_payload["session_id"] = str(session_id)
                if trace_was_truncated:
                    trace_payload["_truncated"] = True
                trace_event.payload = trace_payload

        await db.commit()

    return ApiResponse(
        ok=True,
        data=AttemptFeedback(
            puzzle_id=data["puzzle_id"],
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


@router.get("/sessions/{session_id}/game-state", response_model=ApiResponse)
async def get_game_state(
    session_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
):
    """Gameplay v2: fetch canonical room/object/inventory snapshot.

    Returns an ETag header (weak) based on `game_state_version`.
    On 409 from POST /action, client should re-fetch or use returned snapshot.
    """
    try:
        snapshot = await game_service.get_game_state(db, session_id)
    except game_service.GameplayServiceError as exc:
        body = {
            "ok": False,
            "data": None,
            "error": {"code": exc.code, "message": exc.message},
            "meta": {"interaction_schema_version": 2},
        }
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(body))

    version = snapshot.get("game_state_version", 0)
    etag = f'W/"v{version}"'

    return JSONResponse(
        status_code=200,
        content=jsonable_encoder(
            ApiResponse(
                ok=True,
                data={"game_state": snapshot},
                error=None,
                meta={"interaction_schema_version": 2, "game_state_version": version},
            )
        ),
        headers={"ETag": etag},
    )


@router.post("/sessions/{session_id}/action", response_model=ApiResponse)
async def post_action(
    session_id: uuid.UUID,
    body: ActionRequest,
    db: AsyncSession = Depends(get_db),
):
    """Gameplay v2: apply a declarative action to canonical state."""
    try:
        result = await game_service.apply_action(
            db,
            session_id,
            body.model_dump(),
        )
    except game_service.GameplayServiceError as exc:
        payload = {
            "ok": False,
            "data": None,
            "error": {"code": exc.code, "message": exc.message},
            "meta": {"interaction_schema_version": 2},
        }
        if exc.status_code == 409:
            payload["meta"] = exc.extra.get("meta", payload["meta"])
            payload["data_snapshot"] = exc.extra.get("data_snapshot")
        return JSONResponse(status_code=exc.status_code, content=jsonable_encoder(payload))

    return JSONResponse(status_code=200, content=jsonable_encoder(result))

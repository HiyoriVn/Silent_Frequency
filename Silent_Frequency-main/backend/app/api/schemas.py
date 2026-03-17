"""
Silent Frequency — Pydantic API Schemas

Request / response models for all API endpoints.
These are pure data transfer objects — no business logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


# ──────────────────────────────────────
# Shared envelope
# ──────────────────────────────────────

class ApiMeta(BaseModel):
    timestamp: datetime
    session_id: uuid.UUID


class ApiError(BaseModel):
    code: str
    message: str


class ApiResponse(BaseModel):
    """Standard response envelope."""
    ok: bool = True
    data: Any = None
    error: ApiError | None = None
    meta: ApiMeta | None = None


# ──────────────────────────────────────
# POST /api/sessions  — create session
# ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=64)
    condition: Literal["adaptive", "static"] = "adaptive"


class MasterySnapshot(BaseModel):
    vocabulary: float
    grammar: float
    listening: float


class SessionCreated(BaseModel):
    session_id: uuid.UUID
    player_id: uuid.UUID
    session_token: str
    condition: Literal["adaptive", "static"]
    current_level_index: int
    mastery: MasterySnapshot
    current_room: str


# ──────────────────────────────────────
# GET /api/sessions/{id}/mastery
# ──────────────────────────────────────

class MasteryDetail(BaseModel):
    skill: str
    p_learned: float
    update_count: int
    difficulty_tier: Literal["low", "mid", "high"]


class MasteryResponse(BaseModel):
    session_id: uuid.UUID
    mastery: list[MasteryDetail]
    summary: MasterySnapshot


# ──────────────────────────────────────
# GET /api/sessions/{id}/next-puzzle
# ──────────────────────────────────────

class NextPuzzleResponse(BaseModel):
    puzzle_id: str
    variant_id: str
    skill: str
    slot_order: int
    difficulty_tier: Literal["low", "mid", "high"]
    prompt_text: str
    audio_url: str | None = None
    time_limit_sec: int | None = None
    session_complete: bool


# ──────────────────────────────────────
# POST /api/sessions/{id}/attempts
# ──────────────────────────────────────

class SubmitAttemptRequest(BaseModel):
    variant_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    response_time_ms: int = Field(..., ge=0)
    hint_count_used: int = Field(0, ge=0)


class AttemptFeedback(BaseModel):
    is_correct: bool
    correct_answers: list[str]
    p_learned_before: float
    p_learned_after: float
    difficulty_tier: Literal["low", "mid", "high"]
    current_level_index: int
    session_complete: bool
    mastery: MasterySnapshot

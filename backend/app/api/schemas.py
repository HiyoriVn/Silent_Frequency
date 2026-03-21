"""
Silent Frequency — Pydantic API Schemas

Request / response models for all API endpoints.
These are pure data transfer objects — no business logic.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field


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
    meta: Any = None


# ──────────────────────────────────────
# POST /api/sessions  — create session
# ──────────────────────────────────────

class CreateSessionRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=64)
    condition: Literal["adaptive", "static"] = "adaptive"
    mode: Literal["phase3", "gameplay_v2"] = "phase3"


class MasterySnapshot(BaseModel):
    vocabulary: float
    grammar: float
    listening: float


class SessionCreated(BaseModel):
    session_id: uuid.UUID
    player_id: uuid.UUID
    session_token: str
    condition: Literal["adaptive", "static"]
    mode: Literal["phase3", "gameplay_v2"]
    current_level_index: int
    mastery: MasterySnapshot
    current_room: str


# ──────────────────────────────────────
# Gameplay v2 schema (experimental)
# ──────────────────────────────────────

class GameStateObject(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    type: str
    state: str
    properties: dict[str, Any] = Field(default_factory=dict)


class GameStateInventoryItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    display_name: str
    category: str
    consumed: bool = False
    properties: dict[str, Any] = Field(default_factory=dict)


class HintPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    idle_seconds: int | None = Field(default=None, ge=0)
    failed_attempts_threshold: int | None = Field(default=None, ge=0)


class GameStateSnapshot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_schema_version: Literal[2] = 2
    session_id: uuid.UUID
    game_state_version: int = Field(ge=0)
    updated_at: datetime
    room_id: str
    room_state: list[GameStateObject] = Field(default_factory=list)
    inventory: list[GameStateInventoryItem] = Field(default_factory=list)
    active_puzzles: list[str] = Field(default_factory=list)
    hint_policy: HintPolicy | None = None


class ActionEffect(BaseModel):
    model_config = ConfigDict(extra="forbid")

    type: Literal["add_item", "unlock", "show_dialogue", "open_puzzle"]
    target_id: str | None = None
    item_id: str | None = None
    puzzle_id: str | None = None
    dialogue_id: str | None = None


class ActionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_schema_version: int
    action: Literal["use_item", "inspect", "take_item", "open_object"]
    target_id: str = Field(min_length=1)
    item_id: str | None = None
    client_action_id: uuid.UUID | None = None
    client_ts: str | int | None = None
    game_state_version: int | None = Field(default=None, ge=0)


class ActionResponseData(BaseModel):
    model_config = ConfigDict(extra="forbid")

    effects: list[ActionEffect] = Field(default_factory=list)
    game_state: GameStateSnapshot


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
    interaction_mode: Literal["plain", "scene_hotspot"] = "plain"
    interaction: "InteractionPayload | None" = None
    session_complete: bool


# ──────────────────────────────────────
# POST /api/sessions/{id}/attempts
# ──────────────────────────────────────

class SubmitAttemptRequest(BaseModel):
    variant_id: str = Field(..., min_length=1)
    answer: str = Field(..., min_length=1)
    response_time_ms: int = Field(..., ge=0)
    hint_count_used: int = Field(0, ge=0)
    interaction_trace: list["InteractionTraceEvent"] | None = Field(
        default=None,
        max_length=20,
    )


class AttemptFeedback(BaseModel):
    is_correct: bool
    correct_answers: list[str]
    p_learned_before: float
    p_learned_after: float
    difficulty_tier: Literal["low", "mid", "high"]
    current_level_index: int
    session_complete: bool
    mastery: MasterySnapshot


# ──────────────────────────────────────
# Optional interaction schema (Phase 3)
# ──────────────────────────────────────

class InteractionRectShape(BaseModel):
    model_config = ConfigDict(extra="forbid")

    x: float = Field(..., ge=0.0, le=1.0)
    y: float = Field(..., ge=0.0, le=1.0)
    width: float = Field(..., gt=0.0, le=1.0)
    height: float = Field(..., gt=0.0, le=1.0)


class InteractionHotspotTrigger(BaseModel):
    model_config = ConfigDict(extra="forbid")

    trigger_type: Literal["click"]
    prompt_ref: str | None = None


class InteractionHotspot(BaseModel):
    model_config = ConfigDict(extra="forbid")

    hotspot_id: str = Field(..., min_length=1)
    label: str | None = None
    shape_type: Literal["rect"]
    shape: InteractionRectShape
    trigger: InteractionHotspotTrigger


class InteractionPrompt(BaseModel):
    model_config = ConfigDict(extra="forbid")

    prompt_text: str = Field(..., min_length=1)
    answer_type: Literal["text"]
    correct_answers: list[str] = Field(..., min_length=1)
    max_attempt_chars: int | None = Field(default=None, ge=1)


class InteractionScene(BaseModel):
    model_config = ConfigDict(extra="forbid")

    scene_id: str = Field(..., min_length=1)
    asset_key: str = Field(..., min_length=1)
    instruction_text: str | None = None


class InteractionUIHints(BaseModel):
    model_config = ConfigDict(extra="forbid")

    allow_reopen_prompt: bool | None = None
    show_hotspot_labels: bool | None = None


class InteractionPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_version: Literal[1]
    scene: InteractionScene
    hotspots: list[InteractionHotspot] = Field(..., min_length=1)
    prompts: dict[str, InteractionPrompt] = Field(..., min_length=1)
    ui_hints: InteractionUIHints | None = None


class InteractionTraceEvent(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_type: Literal["hotspot_clicked", "prompt_opened", "prompt_closed"]
    hotspot_id: str | None = None
    prompt_ref: str | None = None
    elapsed_ms: int = Field(..., ge=0)



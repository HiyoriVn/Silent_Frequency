<!-- CHANGELOG: updated 2026-03-21: normalized to English and hardened gameplay v2 contracts with concrete models, version semantics, and pilot-safe constraints -->

# Gameplay Architecture (experimental — gameplay v2)

> **Phase-3 canonical:** The current production flow remains `GET /api/sessions/{session_id}/next-puzzle` + `POST /api/sessions/{session_id}/attempts`. This document defines additive gameplay v2 architecture.

## Executive Summary

Gameplay v2 introduces room/object/inventory interactions using a typed action API and declarative effects. Backend remains the canonical authority for state transitions, progression, scoring, and BKT updates. `POST /api/sessions/{session_id}/attempts` remains the learning puzzle endpoint and coexists with gameplay actions.

## API Surface (v2)

- `GET /api/sessions/{session_id}/game-state`
- `POST /api/sessions/{session_id}/action`
- `POST /api/sessions/{session_id}/attempts` (canonical learning endpoint, unchanged)

All v2 contracts must include `interaction_schema_version: 2`.

Mode and feature-flag enforcement:

- `session.mode` is immutable per session and must be set at creation.
- v2 endpoints must reject requests when `session.mode != gameplay_v2`.
- v2 endpoints must reject requests when `GAMEPLAY_V2_ENABLED=false`.
- Canonical Phase-3 endpoints remain available regardless of v2 flag state.

## Canonical Data Models (Pydantic examples)

```python
from __future__ import annotations

from datetime import datetime
from typing import Literal, Union
from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    code: str
    message: str


class ErrorResponse(BaseModel):
    ok: Literal[False] = False
    data: dict | None = None
    error: ErrorDetail
    meta: dict[str, str | int | None] = Field(default_factory=dict)


class RectShape(BaseModel):
    kind: Literal["rect"] = "rect"
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class ObjectStateSnapshot(BaseModel):
    state: Literal["locked", "unlocked", "revealed", "consumed", "collected"]
    revealed: bool = True


class ObjectModel(BaseModel):
    id: str
    label: str
    shape: RectShape
    interaction_kind: Literal[
        "flavor", "collectible", "clue", "audio", "puzzle_trigger", "locked_container"
    ]
    state: ObjectStateSnapshot
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class ItemModel(BaseModel):
    id: str
    display_name: str
    category: Literal["tool", "clue", "media"]
    consumed: bool = False
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class RoomModel(BaseModel):
    room_id: str
    scene_asset_key: str
    objects: list[ObjectModel]


class UnlockEffect(BaseModel):
    type: Literal["unlock"]
    target_id: str


class RevealEffect(BaseModel):
    type: Literal["reveal"]
    target_id: str


class AddItemEffect(BaseModel):
    type: Literal["add_item"]
    item_id: str


class OpenPuzzleEffect(BaseModel):
    type: Literal["open_puzzle"]
    puzzle_id: str


class ShowDialogueEffect(BaseModel):
    type: Literal["show_dialogue"]
    dialogue_id: str


EffectUnion = Union[UnlockEffect, RevealEffect, AddItemEffect, OpenPuzzleEffect, ShowDialogueEffect]


class GameStateSnapshot(BaseModel):
    interaction_schema_version: Literal[2] = 2
    game_state_version: int = Field(ge=1)
    updated_at: datetime
    room_state: RoomModel
    inventory: list[ItemModel]
    dialogue_queue: list[dict[str, str]] = Field(default_factory=list)


class ActionRequest(BaseModel):
    interaction_schema_version: Literal[2] = 2
    action: Literal["inspect", "collect", "use_item", "open_container", "talk", "trigger"]
    target_id: str
    item_id: str | None = None
    client_action_id: str | None = None
    client_game_state_version: int | None = Field(default=None, ge=1)
    client_ts: datetime | None = None


class ActionResponseData(BaseModel):
    effects: list[EffectUnion]
    room_state: RoomModel
    inventory: list[ItemModel]
    dialogue_queue: list[dict[str, str]] = Field(default_factory=list)
    game_state_version: int = Field(ge=1)
    updated_at: datetime


class ActionResponse(BaseModel):
    ok: Literal[True] = True
    data: ActionResponseData
    error: None = None
    meta: dict[str, str | int] = Field(default_factory=lambda: {"interaction_schema_version": 2})
```

## JSON Schemas (minimal references)

### ActionRequest JSON Schema (minimal)

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["interaction_schema_version", "action", "target_id"],
  "properties": {
    "interaction_schema_version": { "const": 2 },
    "action": {
      "enum": [
        "inspect",
        "collect",
        "use_item",
        "open_container",
        "talk",
        "trigger"
      ]
    },
    "target_id": { "type": "string", "minLength": 1 },
    "item_id": { "type": ["string", "null"] },
    "client_action_id": { "type": ["string", "null"] },
    "client_game_state_version": { "type": ["integer", "null"], "minimum": 1 },
    "client_ts": { "type": ["string", "null"], "format": "date-time" }
  },
  "additionalProperties": false
}
```

## JSON Contract Examples

### GET /api/sessions/{session_id}/game-state

```json
{
  "ok": true,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 21,
    "updated_at": "2026-03-21T10:30:00Z",
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
      "objects": [
        {
          "id": "old_radio",
          "label": "Old Radio",
          "interaction_kind": "puzzle_trigger",
          "state": { "state": "locked", "revealed": true }
        }
      ]
    },
    "inventory": [],
    "dialogue_queue": []
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

### POST /api/sessions/{session_id}/action

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "d4c42187-57f7-4a4c-96ca-e34e8838a2f7",
  "client_game_state_version": 21
}
```

```json
{
  "ok": true,
  "data": {
    "effects": [
      { "type": "unlock", "target_id": "old_radio" },
      { "type": "open_puzzle", "puzzle_id": "listening_radio_01" }
    ],
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
      "objects": [
        {
          "id": "old_radio",
          "label": "Old Radio",
          "interaction_kind": "puzzle_trigger",
          "state": { "state": "unlocked", "revealed": true }
        }
      ]
    },
    "inventory": [
      {
        "id": "bent_key",
        "display_name": "Bent Key",
        "category": "tool",
        "consumed": true
      }
    ],
    "dialogue_queue": [
      { "id": "radio_unlocked", "text": "The radio powers on." }
    ],
    "game_state_version": 22,
    "updated_at": "2026-03-21T10:31:00Z"
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

## `game_state_version` and ETag Semantics

- `game_state_version` is a per-session monotonically increasing integer.
- Server MUST increment it after any canonical state change (object state, inventory, puzzle solved state, dialogue queue changes).
- `GET /api/sessions/{session_id}/game-state` should include `ETag: W/"{session_id}:{game_state_version}"`.
- Clients may send `If-None-Match`; server may return `304 Not Modified` when unchanged.
- When `POST /action` commits successfully, response MUST include the incremented `game_state_version` and `updated_at` from the committed snapshot.

## `client_action_id` Dedupe Semantics

- `client_action_id` is optional but recommended for all mutating actions.
- Dedupe scope: `(session_id, client_action_id)`.
- If duplicate request is received, server should return the previously persisted response payload and status.
- If replay safety cannot be guaranteed (for example partial persistence), return `409` with code `DUPLICATE_ACTION_UNCERTAIN`.

Lightweight migration example for prototype dedupe persistence:

```sql
CREATE TABLE IF NOT EXISTS action_dedupe (
  session_id UUID NOT NULL,
  client_action_id UUID NOT NULL,
  request_hash TEXT NOT NULL,
  response_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (session_id, client_action_id)
);
```

Duplicate replay with previous successful response (`200`):

```json
{
  "ok": true,
  "data": {
    "effects": [{ "type": "unlock", "target_id": "old_radio" }],
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
      "objects": [
        {
          "id": "old_radio",
          "label": "Old Radio",
          "interaction_kind": "puzzle_trigger",
          "state": { "state": "unlocked", "revealed": true }
        }
      ]
    },
    "inventory": [],
    "dialogue_queue": [],
    "game_state_version": 22
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

Unsafe replay (`409`) with canonical state:

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
      "objects": [
        {
          "id": "old_radio",
          "label": "Old Radio",
          "interaction_kind": "puzzle_trigger",
          "state": { "state": "unlocked", "revealed": true }
        }
      ]
    }
  },
  "error": {
    "code": "DUPLICATE_ACTION_UNCERTAIN",
    "message": "Duplicate request detected, but previous commit status is uncertain."
  },
  "meta": { "interaction_schema_version": 2 }
}
```

## HTTP Errors and Standard Envelope

Recommended envelope:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "ACTION_CONFLICT",
    "message": "Object state changed before action application."
  },
  "meta": { "interaction_schema_version": 2 }
}
```

Recommended mapping:

- `400 Bad Request`: invalid schema, unsupported action, invalid target payload.
- `401 Unauthorized`: session token missing/expired.
- `403 Forbidden`: session exists but actor is not allowed to mutate.
- `404 Not Found`: session, room, object, or item not found.
- `409 Conflict`: stale state, lock contention, duplicate/unsafe replay.
- `500 Internal Server Error`: unexpected backend failures.

Stale state conflict (`409`) example:

```json
{
  "ok": false,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 22,
    "updated_at": "2026-03-21T10:33:00Z",
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
      "objects": []
    },
    "inventory": [],
    "dialogue_queue": []
  },
  "error": {
    "code": "CONFLICT_STALE_STATE",
    "message": "client_game_state_version is stale."
  },
  "meta": { "interaction_schema_version": 2 }
}
```

## Auto-hint Policy (v2)

Hint behavior should be backend-configurable and telemetry-visible.

Configuration options:

- `idle_seconds`: time without meaningful action before auto-hint suggestion.
- `failed_attempts_threshold`: number of failed puzzle attempts before stronger hint.
- `auto_hint_enabled`: hard on/off switch for pilot control.

Configuration example:

```json
{
  "hint_policy": {
    "idle_seconds": 60,
    "failed_attempts_threshold": 3,
    "auto_hint_enabled": true
  }
}
```

Required telemetry event:

- `hint_opened` with fields:
  - `session_id`
  - `hint_id`
  - `hint_type` (`inventory|auto`)
  - `timestamp`
  - `trigger_context` (optional)

## Concurrency and Atomicity

- Action resolution must be atomic: validate preconditions, apply effects, persist state, emit `game_action` telemetry, and return canonical state in one DB transaction.
- Effects are applied as one all-or-nothing unit. If one effect fails validation, none of the effects are committed.
- Successful action responses MUST return both `effects[]` and committed canonical `room_state` plus `inventory`.
- On conflict, return `409` with machine-readable code and the latest canonical snapshot (`room_state`, `inventory`, `game_state_version`, `updated_at`).
- Clients should treat server response as authoritative and reconcile local UI state immediately.

## Telemetry Contract

- `game_action` is required for each resolved action.
- `puzzle_interaction_trace` remains available for puzzle interaction telemetry.

`game_action` minimum fields:

- `session_id`
- `action`
- `target_id`
- `item_id` (nullable)
- `client_action_id` (optional)
- `timestamp`
- `resulting_effects[]`

## Asset and Seed Notes

For content and asset conventions, use:

- `docs/puzzle_content_system.md` for room/object/item schemas and asset conventions.
- `docs/seeding_guide.md` for `rooms/*.json`, `items/*.json`, validation checks, and seed failure codes.

Keep canonical puzzle files in `backend/app/content/puzzles/` unchanged for Phase-3 compatibility.

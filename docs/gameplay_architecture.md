<!-- CHANGELOG: updated 2026-03-21: normalized to English and expanded gameplay v2 schemas, HTTP semantics, dedupe, and auto-hint policy -->

# Gameplay Architecture (experimental - gameplay v2)

> **Phase-3 canonical:** The current production flow remains `GET /api/sessions/{id}/next-puzzle` + `POST /api/sessions/{id}/attempts`. This document defines additive gameplay v2 architecture.

## Executive Summary

Gameplay v2 introduces room/object/inventory interactions using a typed action API and declarative effects. Backend remains the canonical authority for state transitions, progression, scoring, and BKT updates. `POST /api/sessions/{id}/attempts` remains the learning puzzle endpoint and coexists with gameplay actions.

## API Surface (v2)

- `GET /api/sessions/{id}/game-state`
- `POST /api/sessions/{id}/action`
- `POST /api/sessions/{id}/attempts` (canonical learning endpoint, unchanged)

All v2 contracts must include `interaction_schema_version: 2`.

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
    meta: dict[str, str | int | None] = {}


class ObjectState(BaseModel):
    state: Literal["locked", "unlocked", "revealed", "consumed", "collected"]
    revealed: bool = True


class ObjectModel(BaseModel):
    id: str
    label: str
    interaction_kind: Literal[
        "flavor", "collectible", "clue", "audio", "puzzle_trigger", "locked_container"
    ]
    state: ObjectState


class Item(BaseModel):
    id: str
    display_name: str
    category: Literal["tool", "clue", "media"]
    consumed: bool = False


class Room(BaseModel):
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
    room_state: Room
    inventory: list[Item]
    dialogue: list[dict[str, str]]


class ActionRequest(BaseModel):
    interaction_schema_version: Literal[2] = 2
    action: Literal["inspect", "collect", "use_item", "open_container", "talk", "trigger"]
    target_id: str
    item_id: str | None = None
    client_action_id: str | None = None
    client_ts: datetime | None = None


class ActionResponse(BaseModel):
    ok: Literal[True] = True
    data: dict
    error: None = None
    meta: dict[str, str | int] = {"interaction_schema_version": 2}
```

## JSON Contract Examples

### GET /api/sessions/{id}/game-state

```json
{
  "ok": true,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 21,
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
    "dialogue": []
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

### POST /api/sessions/{id}/action

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "d4c42187-57f7-4a4c-96ca-e34e8838a2f7"
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
      { "id": "bent_key", "display_name": "Bent Key", "category": "tool", "consumed": true }
    ],
    "dialogue": [
      { "id": "radio_unlocked", "text": "The radio powers on." }
    ],
    "game_state_version": 22
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

## `game_state_version` and ETag Semantics

- `game_state_version` is a per-session monotonically increasing integer.
- Server MUST increment it after any canonical state change (object state, inventory, puzzle solved state, dialogue queue changes).
- `GET /api/sessions/{id}/game-state` should include `ETag: W/"{session_id}:{game_state_version}"`.
- Clients may send `If-None-Match`; server may return `304 Not Modified` when unchanged.

## `client_action_id` Dedupe Semantics

- `client_action_id` is optional but recommended for all mutating actions.
- Dedupe scope: `(session_id, client_action_id)`.
- If duplicate request is received, server should return the previously persisted response payload and status.
- If replay safety cannot be guaranteed (for example partial persistence), return `409` with code `DUPLICATE_ACTION_UNCERTAIN`.

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

## Auto-hint Policy (v2)

Hint behavior should be backend-configurable and telemetry-visible.

Configuration options:

- `idle_seconds`: time without meaningful action before auto-hint suggestion.
- `failed_attempts_threshold`: number of failed puzzle attempts before stronger hint.

Required telemetry event:

- `hint_opened` with fields:
  - `session_id`
  - `hint_type` (`inventory|auto`)
  - `hint_id`
  - `timestamp`
  - `trigger_context` (optional)

## Concurrency and Atomicity

- Action resolution must be atomic: validate preconditions, apply effects, persist state, emit `game_action` telemetry, and return canonical state in one transaction boundary.
- On conflict, return `409` with machine-readable code and the latest canonical `room_state`.
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


<!-- CHANGELOG: updated 2026-03-21: normalized to English and expanded gameplay v2 room/object/item schema and asset guidance -->

# Puzzle Content System

## Overview

> **Phase-3 canonical:** The puzzle JSON format in `backend/app/content/puzzles/` remains the canonical production format for learning puzzles.

Silent Frequency puzzle content is file-driven.
Puzzle definitions live in JSON files under:

- `backend/app/content/puzzles/`

Each file defines one puzzle and exactly three variants: `low`, `mid`, `high`.
The backend seed process reads these files and writes:

- `puzzles` rows
- `puzzle_variants` rows

## Puzzle JSON Schema

Each file follows this shape:

```json
{
  "puzzle_id": "start_vocab_sign",
  "skill": "vocabulary",
  "slot_order": 1,
  "title": "Translate the Warning Sign",
  "room": "start_room",
  "mechanic": "translation",
  "max_hints": 2,
  "variants": {
    "low": {
      "prompt_text": "...",
      "answer_type": "text",
      "correct_answers": ["..."],
      "audio_url": null,
      "time_limit_sec": null,
      "hints": ["...", "..."]
    },
    "mid": {
      "prompt_text": "...",
      "answer_type": "text",
      "correct_answers": ["..."],
      "audio_url": null,
      "time_limit_sec": null,
      "hints": ["...", "..."]
    },
    "high": {
      "prompt_text": "...",
      "answer_type": "text",
      "correct_answers": ["..."],
      "audio_url": null,
      "time_limit_sec": null,
      "hints": ["...", "..."]
    }
  }
}
```

## Skill / Slot / Tier Logic

Progression is backend-owned and fixed:

1. vocabulary slot 1
2. vocabulary slot 2
3. vocabulary slot 3
4. grammar slot 1
5. grammar slot 2
6. grammar slot 3
7. listening slot 1
8. listening slot 2
9. listening slot 3

Tier policy:

- slot 1 is always `mid`
- static sessions always use `mid`
- adaptive sessions use BKT to choose `low` / `mid` / `high` on later slots

## Difficulty Design Rules

For each puzzle file, keep **mechanic constant** across tiers.
Only increase complexity by tier:

- `low`: IELTS ~0-2.5
- `mid`: IELTS ~3-4.5
- `high`: IELTS ~5-5.5

Change only:

- language complexity
- grammar difficulty
- listening complexity

Do not change puzzle objective or core interaction pattern by tier.

## Listening Notes

Current listening variants use:

- `"audio_url": null`

Audio delivery is intentionally deferred. Add real TTS/audio URLs later without changing puzzle IDs.

## How to Add a New Puzzle

1. Add one JSON file in `backend/app/content/puzzles/`.
2. Use a unique `puzzle_id`.
3. Set valid `skill` (`vocabulary`, `grammar`, `listening`).
4. Use a valid `room` (`start_room`, `radio_room`, `lab_room`).
5. Provide all three variants (`low`, `mid`, `high`).
6. Ensure each variant has non-empty `correct_answers`.
7. Ensure hint count does not exceed `max_hints`.
8. Run seed script and verify inserts/updates.

## Best Practices

- Keep `correct_answers` as short normalized strings.
- Include multiple acceptable phrasings when needed.
- Keep prompts concise and task-oriented.
- Use stable IDs; avoid renaming existing `puzzle_id` values.
- Treat JSON files as source of truth; avoid hardcoded puzzle data in Python.

## Room/Object/Item Schema (experimental — gameplay v2)

> **experimental — gameplay v2:** Additive content model for room interactions. Existing puzzle files in `puzzles/` remain unchanged.

### Room JSON (example)

```json
{
  "interaction_schema_version": 2,
  "room_id": "radio_room_v2",
  "scene": {
    "asset_key": "scene_radio_room_v2",
    "asset_path": "/scenes/radio_room_v2.png"
  },
  "hotspots": [
    { "hotspot_id": "hs_radio", "object_id": "old_radio" },
    { "hotspot_id": "hs_drawer", "object_id": "desk_drawer" }
  ],
  "objects": [
    {
      "id": "old_radio",
      "label": "Old Radio",
      "shape": { "kind": "rect", "x": 0.41, "y": 0.22, "w": 0.18, "h": 0.24 },
      "interaction_kind": "puzzle_trigger",
      "initial_state": { "locked": true, "revealed": true, "collected": false },
      "metadata": { "puzzle_id": "listening_radio_01" }
    }
  ]
}
```

### Object JSON (standalone example)

```json
{
  "interaction_schema_version": 2,
  "id": "desk_drawer",
  "label": "Desk Drawer",
  "shape": { "kind": "rect", "x": 0.62, "y": 0.53, "w": 0.2, "h": 0.2 },
  "interaction_kind": "locked_container",
  "initial_state": { "locked": true, "revealed": true, "collected": false },
  "metadata": { "unlock_item_id": "bent_key" }
}
```

### Item JSON (example)

```json
{
  "interaction_schema_version": 2,
  "id": "note_fragment_1",
  "display_name": "Torn Note Fragment",
  "category": "clue",
  "payload": {
    "text": "FM 87.5 ... midnight",
    "audio_url": null,
    "fragment_id": "note_f1"
  },
  "reusable": true
}
```

### Pydantic Models (example)

```python
from typing import Literal
from pydantic import BaseModel, Field


class ObjectState(BaseModel):
    locked: bool = False
    revealed: bool = True
    collected: bool = False


class RectShape(BaseModel):
    kind: Literal["rect"] = "rect"
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class ObjectModel(BaseModel):
    id: str
    label: str
    shape: RectShape
    interaction_kind: Literal[
        "flavor", "collectible", "clue", "audio", "puzzle_trigger", "locked_container"
    ]
    initial_state: ObjectState
    metadata: dict[str, str | int | bool | None] = Field(default_factory=dict)


class ItemModel(BaseModel):
    interaction_schema_version: Literal[2] = 2
    id: str
    display_name: str
    category: Literal["tool", "clue", "media"]
    payload: dict[str, str | None]
    reusable: bool = False
```

### JSON Schema Snippets (compact)

`RoomDefinition` (minimal):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": ["interaction_schema_version", "room_id", "objects"],
  "properties": {
    "interaction_schema_version": { "const": 2 },
    "room_id": { "type": "string", "pattern": "^[a-z0-9_]+$" },
    "objects": {
      "type": "array",
      "items": {
        "type": "object",
        "required": [
          "id",
          "label",
          "shape",
          "interaction_kind",
          "initial_state"
        ],
        "properties": {
          "id": { "type": "string", "pattern": "^[a-z0-9_]+$" },
          "shape": {
            "type": "object",
            "required": ["kind", "x", "y", "w", "h"],
            "properties": {
              "kind": { "const": "rect" },
              "x": { "type": "number", "minimum": 0, "maximum": 1 },
              "y": { "type": "number", "minimum": 0, "maximum": 1 },
              "w": { "type": "number", "exclusiveMinimum": 0, "maximum": 1 },
              "h": { "type": "number", "exclusiveMinimum": 0, "maximum": 1 }
            }
          }
        }
      }
    }
  }
}
```

`ItemDefinition` (minimal):

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "interaction_schema_version",
    "id",
    "display_name",
    "category",
    "payload"
  ],
  "properties": {
    "interaction_schema_version": { "const": 2 },
    "id": { "type": "string", "pattern": "^[a-z0-9_]+$" },
    "display_name": { "type": "string", "minLength": 1 },
    "category": { "enum": ["tool", "clue", "media"] },
    "payload": { "type": "object" },
    "reusable": { "type": "boolean" }
  }
}
```

### Naming Conventions (gameplay v2)

- IDs are lowercase snake_case (`room_id`, `object_id`, `item_id`, `hotspot_id`, `puzzle_id`).
- Scene assets should use stable keys and matching file names (`scene_radio_room_v2` -> `radio_room_v2.png`).
- Keep IDs immutable after shipping to avoid broken saves, telemetry joins, and replay mismatches.

### Effects Array (example)

```json
{
  "interaction_schema_version": 2,
  "effects": [
    { "type": "unlock", "target_id": "desk_drawer" },
    { "type": "reveal", "target_id": "drawer_note" },
    { "type": "add_item", "item_id": "note_fragment_1" },
    { "type": "open_puzzle", "puzzle_id": "grammar_panel_02" }
  ]
}
```

### Asset Conventions

- Prototype asset locations:
  - `frontend/public/scenes/` for room backgrounds.
  - `frontend/public/objects/` for object overlays/icons.
- Allowed formats: `.png`, `.jpg`, `.svg`.
- Recommended resolutions:
  - Scene backgrounds: base 1920x1080.
  - Object overlays/icons: 256x256 or 512x512 depending on complexity.
- Retina guideline: provide 2x assets where detail matters (`@2x`) and map by `asset_key`/metadata.
- Optional backend asset serving is allowed for signed URLs or access control, but static frontend assets are simpler and lower latency for prototypes.

### Seed Guidance

- Place room definitions in `backend/app/content/rooms/`.
- Place item definitions in `backend/app/content/items/`.
- Keep `backend/app/content/puzzles/` unchanged for canonical learning content.
- Validate references between room objects, item IDs, and puzzle IDs during seed.

<!-- CHANGELOG: pass-2 canonical rewrite preserving puzzle, room, item, schema, and seed validation detail -->

# Puzzle and Content System

## Scope

This document defines the authored content model for Silent Frequency.

It covers:

- canonical learning puzzle files
- gameplay v2 room and item authoring
- tier and slot rules
- asset conventions
- validation rules
- seeding expectations

> **Phase-3 canonical:** The puzzle JSON format in `backend/app/content/puzzles/` remains the canonical production format for learning puzzles.

---

## 1. Content Locations

Current authored content roots:

- `backend/app/content/puzzles/`
- `backend/app/content/rooms/`
- `backend/app/content/items/` for gameplay v2 item definitions

Suggested structure:

```text
backend/app/content/
  puzzles/
  rooms/
    radio_room_v2.json
  items/
    note_fragment_1.json
```

---

## 2. Chapter Prototype Content Model

The current thesis prototype is organized as a single playable chapter rather than a full multi-chapter shipped product.

### Chapter Authoring Structure

A chapter may contain:

- one primary map
- multiple connected zones or sub-rooms
- a finite set of interactable objects
- a bounded inventory
- a gated puzzle graph
- one final escape or completion condition

Example conceptual chapter zones:

- patient room
- nurse station
- hallway
- security office
- exit area

### Design Rule

A chapter should feel like one coherent escape scenario.

Do not author it as a disconnected list of quiz screens with decorative background art.

---

## 3. Canonical Puzzle Content

Each puzzle file defines one puzzle and exactly three variants:

- `low`
- `mid`
- `high`

The backend seed process reads these files and writes:

- `puzzles` rows
- `puzzle_variants` rows

### Canonical Puzzle JSON Shape

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

### Canonical Rules

- every file must define one unique `puzzle_id`
- each puzzle must belong to a valid `skill`
- each puzzle must have one valid `slot_order`
- all three variants must be present
- each variant must contain non-empty `correct_answers`
- hint count must not exceed `max_hints`

---

## 4. Skill, Slot, and Tier Logic

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
- adaptive sessions use BKT to choose `low`, `mid`, or `high` on later slots

Prototype note:

Pre-test or initialization logic may use finer-grained participant grouping where useful, but runtime gameplay currently maps these results into the supported puzzle tiers:

- `low`
- `mid`
- `high`

This avoids requiring a full parallel content bank for every possible initialization band.

### Difficulty Design Rule

Keep the **mechanic constant** across tiers.

Only increase complexity by tier, for example:

- language complexity
- grammar difficulty
- listening complexity

Do not change the core puzzle objective across tiers.

---

## 5. Mechanic Reuse Rule for Prototype Scope

For the prototype, the same core puzzle mechanic may be reused across multiple authored puzzles with different content.

### Recommended Rule

Reuse a small number of core mechanics across the chapter, for example:

- hidden object / environmental inspection
- item use and multi-step item chains
- code or lock puzzles
- cipher / hidden-message puzzles
- narrative clue combination for final unlock

### Constraint

Do not create a large number of unrelated mechanics for a short prototype.

The preferred approach is:

- fewer mechanics
- more coherent reuse
- stronger narrative and object integration
- variation through content, clue structure, and difficulty tier

---

## 6. World-state and FSM-style Gating

Puzzle availability in the chapter is constrained by canonical world state.

A puzzle may be opened only when its gating requirements are satisfied.

### Typical Gating Inputs

- current zone or room
- object visibility or reveal state
- lock/unlock state
- required item possession
- prior puzzle completion
- narrative or dialogue trigger state

### Authoring Rule

Content authors should model progression as a gated graph, not as a flat unordered puzzle pool.

### Example

A listening puzzle tied to a radio should not open until:

- the player has reached the relevant zone
- the radio is revealed
- power or battery conditions are satisfied
- the radio interaction returns `open_puzzle`

---

## 7. Vocabulary Board and Knowledge Journal

The chapter prototype may expose a vocabulary-support layer that helps players understand objects, clues, and previously solved puzzle content.

### Purpose

This layer supports:

- contextual vocabulary learning
- object comprehension
- clue review
- bilingual scaffolding for the target audience

### Suggested Contents

A vocabulary or journal entry may contain:

- object label in English
- Vietnamese meaning
- short object function or gameplay role
- related clue note
- solved-puzzle explanation where appropriate

### Rule

The vocabulary board is a support and reflection layer.

It must not directly bypass puzzle progression by revealing final answers automatically.

---

## 8. Bilingual Content Rules

The thesis prototype uses a bilingual presentation model.

### Recommended Semantics

- environment-facing content such as object labels, signs, and puzzle text is primarily in English
- support text such as hints, internal monologue, and assistant guidance is primarily in Vietnamese
- glossary or vocabulary explanations may be bilingual
- critical UX instructions may be bilingual when clarity requires it

### Rule

Keep language-role boundaries consistent across the chapter so the player can distinguish:

- world input
- support scaffolding
- narrative reflection

---

## 9. Room and Asset Authoring Rules

Room and object content should be authored together with visual asset assumptions.

### Room-level Rules

Each playable zone should define:

- `zone_id` or stable room/area identifier
- background scene asset
- interactable objects
- traversal connections if applicable
- narrative purpose
- puzzle or clue role

### Recommended Zone Types

For a chapter prototype, authored zones should usually fall into one of the following roles:

- `puzzle_zone`: contains a primary puzzle trigger or multi-step interaction
- `traversal_zone`: connects major spaces and supports navigation, pacing, or environmental storytelling
- `narrative_zone`: emphasizes dialogue, clue reading, or story revelation
- `reward_zone`: delivers payoff, major clue resolution, or final escape progression

### Rule

Not every zone should contain a full puzzle.

A coherent prototype chapter usually mixes high-interaction zones with lighter connective zones.

### Object-level Rules

Each interactable object should have:

- stable object ID
- clear gameplay role
- visual state assumptions when relevant
- optional vocabulary/journal metadata
- optional linked puzzle or item metadata

### Required Object Categories for a Chapter Prototype

A strong prototype chapter should include a mix of:

- clue objects
- locked containers
- collectible items
- puzzle-trigger objects
- traversal or exit objects

### Visual State Guidance

Where relevant, object authoring should anticipate at least:

- default
- highlighted or focusable
- unlocked/opened/revealed
- collected/disabled

These may initially be implemented through overlays or UI feedback rather than separate full-detail art assets.

### Naming Guidance for Chapter Prototypes

For multi-zone chapters, use stable identifiers that reflect both chapter and zone context where useful.

Example patterns:

- `chapter_id`: `st_mary_hospital`
- `zone_id`: `patient_room_404`
- `object_id`: `patient_room_404_clipboard`
- `puzzle_id`: `patient_room_404_warning_note`

Prefer stable descriptive IDs over short temporary names.

---

## 10. Asset Consistency Rules for AI-assisted Production

When visual assets are generated with AI tools, consistency is more important than raw detail.

### Required Consistency Dimensions

- art style
- lighting mood
- color palette
- camera angle or framing
- object naming
- scene naming
- chapter setting continuity

### Recommended Workflow

1. define a chapter style guide first
2. define room and object lists
3. define naming conventions
4. generate background and object assets against the same style constraints
5. cut out, clean, and integrate only after IDs and usage are stable

### Rule

Do not generate assets before room structure, object roles, and naming rules are frozen.

---

## 11. Batch-2 Interaction Metadata for Canonical Puzzles

Batch-2 interactive Phase-3 puzzles may define additive interaction metadata.

### Supported Interaction Model

- trigger type: `click` only
- shape type: `rect` only
- multiple hotspots allowed
- exactly one hotspot must include `trigger.prompt_ref`
- every used `prompt_ref` must exist in `prompts`
- no scripting, conditions, transitions, or state-machine fields

### Data Flow

Content -> seed validation -> variant metadata -> next-puzzle API -> frontend render -> attempt submit -> event log telemetry

### Example Interaction Fragment

```json
{
  "interaction": {
    "prompts": {
      "p1": "Translate the warning sign."
    },
    "hotspots": [
      {
        "hotspot_id": "sign_1",
        "shape": { "kind": "rect", "x": 0.12, "y": 0.24, "w": 0.16, "h": 0.21 },
        "trigger": { "prompt_ref": "p1" }
      }
    ]
  }
}
```

---

## 12. Gameplay v2 Room Content

> **experimental — gameplay v2:** Additive content model for room interactions. Existing puzzle files remain unchanged.

### Room JSON Example

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

### Standalone Object Example

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

### Item JSON Example

```json
{
  "interaction_schema_version": 2,
  "item_id": "screwdriver_01",
  "display_name": "Screwdriver",
  "category": "tool",
  "reusable": true
}
```

---

## 13. Runtime vs Authoring Semantics

### Item Semantics

`reusable: bool` belongs to the **item definition / authored content model**.

It describes whether an item survives use by design.

`consumed: bool` belongs to the **runtime inventory snapshot** returned in API responses.

These are not contradictory:

- authoring defines reusable intent
- runtime state reflects whether a particular item instance has been consumed

Do not add `consumed` to item definition files.

### Object State Semantics

Content authoring uses explicit boolean flags in `initial_state`, such as:

- `locked`
- `revealed`
- `collected`

This is the canonical authoring format.

Runtime snapshots may currently use enum-like state plus boolean flags. Avoid introducing new mixed models unless a future schema revision explicitly harmonizes them.

---

## 14. Pydantic-style Model Examples

### Canonical Gameplay v2 Authoring Models

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
    item_id: str
    display_name: str
    category: Literal["tool", "clue", "media"]
    payload: dict[str, str | None]
    reusable: bool = False
```

---

## 15. JSON Schema Snippets

### `RoomDefinition` Minimal Example

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

### `ItemDefinition` Minimal Example

```json
{
  "$schema": "https://json-schema.org/draft/2020-12/schema",
  "type": "object",
  "required": [
    "interaction_schema_version",
    "item_id",
    "display_name",
    "category",
    "payload"
  ],
  "properties": {
    "interaction_schema_version": { "const": 2 },
    "item_id": { "type": "string", "pattern": "^[a-z0-9_]+$" },
    "display_name": { "type": "string", "minLength": 1 },
    "category": { "enum": ["tool", "clue", "media"] },
    "payload": { "type": "object" },
    "reusable": { "type": "boolean" }
  }
}
```

---

## 16. Effects Array Shape

Effects are returned in API responses and should remain declarative.

Example:

```json
{
  "ok": true,
  "data": {
    "effects": [
      { "type": "unlock", "target_id": "desk_drawer" },
      { "type": "reveal", "target_id": "drawer_note" },
      { "type": "add_item", "item_id": "note_fragment_1" },
      { "type": "open_puzzle", "puzzle_id": "grammar_panel_02" }
    ],
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    },
    "inventory": []
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

---

## 17. Asset Conventions

Recommended prototype asset locations:

- `frontend/public/scenes/{asset_key}.png`
- `frontend/public/objects/{asset_key}.png`

Allowed formats:

- `.png`
- `.jpg`
- `.svg`

Guidelines:

- provide 1x and 2x assets where detail matters
- keep hotspot coordinates functional even if an image fallback is shown
- recommended scene base resolution: 1920x1080

### Naming Rules

- IDs are lowercase snake_case:
  - `room_id`
  - `object_id`
  - `item_id`
  - `hotspot_id`
  - `puzzle_id`

- scene assets should use stable keys and matching filenames
- avoid renaming shipped IDs because telemetry joins, replay, and seed references depend on stability

---

## 18. Seeding Rules

### Canonical Puzzle Seeding

`backend/app/seed.py` currently:

1. validates content shape and required fields
2. validates no duplicate puzzle IDs
3. validates no duplicate `(skill, slot_order)` pairs
4. validates each skill has slot coverage `1,2,3`
5. inserts or updates `skills`
6. inserts or updates `puzzles`
7. inserts or updates `puzzle_variants`

This process should remain idempotent and safe to repeat in development.

### Gameplay v2 Content Validation

Validator checklist for v2 files:

- `interaction_schema_version` must be `2`
- object IDs must be unique within a room
- hotspots must reference valid object IDs
- `metadata.puzzle_id` and `metadata.item_id` references must exist
- shape coordinates must remain in `[0.0, 1.0]`
- no scripting sections are allowed
- failures must exit non-zero with descriptive codes/messages

Recommended validation order:

1. parse and schema-check each file independently
2. build in-memory indexes for rooms, objects, items, and puzzle IDs
3. resolve cross-references
4. abort before persistence if any validation step fails

### Recommended Seed Failure Codes

- `2` = schema validation error
- `3` = missing reference
- `4` = geometry invalid
- `5` = duplicate ID

Example message:

```text
SEED_REFERENCE_ERROR: room 'radio_room_v2' hotspot 'hs_radio' references unknown object_id 'old_radio_typo'.
```

Preferred line-aware format when available:

```text
SEED_VALIDATION_ERROR: backend/app/content/rooms/radio_room_v2.json:27:15: field 'interaction_kind' must be one of ['flavor','collectible','clue','audio','puzzle_trigger','locked_container'].
```

---

## 19. Contributor Checklist

When adding new content:

1. use stable unique IDs
2. keep content declarative
3. avoid hardcoded runtime logic
4. validate seed behavior locally
5. verify affected tests
6. confirm frontend can render the new content shape without ad hoc compatibility hacks

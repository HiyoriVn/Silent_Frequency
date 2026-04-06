<!-- CHANGELOG: updated 2026-03-21: normalized to English and added gameplay v2 seed validation and error-code guidance -->

# Seeding Guide

## What the Seed System Does

> **Phase-3 canonical:** The current puzzle seeding process for `backend/app/content/puzzles/` remains canonical and backward-compatible.

`backend/app/seed.py` loads JSON puzzle definitions from:

- `backend/app/content/puzzles/`

Then it:

1. Validates content shape and required fields.
2. Validates no duplicate puzzle IDs.
3. Validates no duplicate `(skill, slot_order)` pairs.
4. Validates each skill has slot coverage `1,2,3`.
5. Inserts or updates `skills`.
6. Inserts or updates `puzzles`.
7. Inserts or updates `puzzle_variants`.

This is idempotent and safe to run repeatedly in development.

## Add New Content

1. Create a new `.json` file in `backend/app/content/puzzles/`.
2. Follow schema documented in `docs/puzzle_content_system.md`.
3. Run seed script.
4. Check output summary for inserted/updated counts.

## Run Seed Script

From workspace root:

```bash
python -m backend.app.seed
```

Expected output includes counts like:

- skills inserted/updated
- puzzles inserted/updated
- variants inserted/updated

## Troubleshooting

### Duplicate Data

Symptoms:

- validation error about duplicate puzzle IDs or duplicate skill-slot mapping

Fix:

1. Search JSON files for repeated `puzzle_id`.
2. Ensure each skill uses unique `slot_order` values.

### Schema Mismatch

Symptoms:

- validation error about missing keys
- validation error about missing tiers or invalid value types

Fix:

1. Compare the file with the required schema in `docs/puzzle_content_system.md`.
2. Ensure `variants` has exactly `low`, `mid`, `high`.
3. Ensure `correct_answers` is a non-empty string list.

### Existing Database Has Legacy Data

Symptoms:

- unexpected behavior from older records

Fix (early-stage safe option):

1. Drop/recreate local database.
2. Re-run seed script.

Because this project is still early-stage, local reset is acceptable when schema/content assumptions change.

## Gameplay v2 Content Locations (experimental — gameplay v2)

> **experimental — gameplay v2:** Additive seeding support for room/object/item content. Existing puzzle seeding remains unchanged.

### Content Placement

- Rooms: `backend/app/content/rooms/*.json`
- Items: `backend/app/content/items/*.json`
- Puzzles remain in: `backend/app/content/puzzles/*.json`

Suggested tree:

```text
backend/app/content/
  puzzles/
  rooms/
    radio_room_v2.json
  items/
    note_fragment_1.json
```

### Validator Checklist for v2 Files

- File-level: `interaction_schema_version` must be `2`.
- Object IDs must be unique within a room.
- Hotspots must reference valid object IDs.
- `metadata.puzzle_id` and `metadata.item_id` references must exist in puzzles/items.
- Shape coordinates (`x`, `y`, `w`, `h`) must all be in `[0.0,1.0]`.
- No scripting sections are allowed in JSON; declarative fields only.
- On validation failure, seed must exit non-zero with descriptive code/message.

Recommended validator execution order:

1. Parse and schema-check each file independently.
2. Build in-memory indexes for rooms, objects, items, and puzzle IDs.
3. Resolve cross-references (hotspots, unlock items, puzzle links).
4. Abort before persistence if any validation step fails.

### Seed Failure Behavior

If seed detects invalid references, it should exit with clear codes/messages.

Recommended mapping:

- `2` = schema validation error.
- `3` = missing reference (puzzle/item/object).
- `4` = geometry invalid.
- `5` = duplicate ID.

Example failure message:

```text
SEED_REFERENCE_ERROR: room 'radio_room_v2' hotspot 'hs_radio' references unknown object_id 'old_radio_typo'.
```

Line-level error guidance:

- Include file path and line/column when available.
- Preferred format: `<ERROR_CODE>: <file>:<line>:<column>: <message>`.
- Example:

```text
SEED_VALIDATION_ERROR: backend/app/content/rooms/radio_room_v2.json:27:15: field 'interaction_kind' must be one of ['flavor','collectible','clue','audio','puzzle_trigger','locked_container'].
```

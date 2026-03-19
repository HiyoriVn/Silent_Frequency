# Seeding Guide

## What the Seed System Does

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

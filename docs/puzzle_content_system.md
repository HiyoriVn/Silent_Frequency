# Puzzle Content System

## Overview

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

Audio delivery is intentionally deferred (coming soon). Add real TTS/audio URLs later without changing puzzle IDs.

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

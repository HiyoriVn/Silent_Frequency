# Silent Frequency Session Flow (Phase 2)

Date: 2026-03-17
Scope: Backend session-flow redesign only

## Session Lifecycle

The backend now owns session progression through a fixed 9-step script.

Progression script:

1. vocabulary, slot 1
2. vocabulary, slot 2
3. vocabulary, slot 3
4. grammar, slot 1
5. grammar, slot 2
6. grammar, slot 3
7. listening, slot 1
8. listening, slot 2
9. listening, slot 3

Lifecycle steps:

1. Client calls session creation with player name and condition (`adaptive` or `static`).
2. Backend creates player, game session, initial BKT estimates, and game state.
3. Backend sets `current_level_index = 0`.
4. Client asks for next puzzle using only session ID.
5. Backend resolves skill and slot from `current_level_index`.
6. Backend returns exactly one puzzle variant for that level.
7. Client submits attempt.
8. Backend scores answer, updates BKT, logs attempt/event, increments `current_level_index`.
9. At level index 9, backend marks session complete.

## API Flow

Session start:

- `POST /api/sessions`
- Input includes: `display_name`, `condition`
- Output includes: `condition`, `current_level_index`

Get next puzzle:

- `GET /api/sessions/{session_id}/next-puzzle`
- No skill query is required.
- Backend decides skill, slot, and variant.
- Response includes: `slot_order` and `session_complete`.

Submit attempt:

- `POST /api/sessions/{session_id}/attempts`
- Backend updates BKT and session progression index.
- Response now includes: `current_level_index`, `session_complete`.

## Backend Ownership

Backend ownership in this phase means:

1. Client no longer asks for puzzle by skill.
2. Backend controls which skill/slot comes next.
3. Backend controls completion state (`session_complete`).
4. Session condition is stored server-side and used for tier policy.

Difficulty policy in this phase:

1. Slot 1 is always `mid`.
2. If condition is `static`, all slots use `mid`.
3. If condition is `adaptive`, slot 2-3 use BKT-based tier selection.

## Data Flow

Core session state fields:

- `condition`
- `current_level_index`

How state moves:

1. Created in session service at session start.
2. Read in puzzle selection for level resolution.
3. Updated in attempt submission after each answer.
4. Used to determine `session_complete`.

Logging touched by this flow:

1. `attempt_submitted` event remains in place.
2. `session_progressed` event is written after level advancement.
3. Attempt table still records answer quality and timing.

## Maintenance Notes

For student maintainers:

1. Keep progression decisions in backend services, not in frontend phase state.
2. Do not bypass `current_level_index` when adding or debugging routes.
3. If you change level count, update the level script in one place and verify completion logic.
4. Keep static/adaptive condition behavior simple and explicit.
5. Preserve BKT engine isolation; session flow should call it, not rewrite it.
6. Validate API contract changes with backend and frontend types together.

This document describes the current Phase 2 session-flow refactor only. It does not introduce engine redesign or new gameplay features.

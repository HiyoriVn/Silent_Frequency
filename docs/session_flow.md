<!-- CHANGELOG: updated 2026-03-21: normalized to English and added exploratory gameplay-mode-v2 API semantics -->

# Silent Frequency Session Flow (Phase 2)

Date: 2026-03-17
Scope: Backend session-flow redesign only

## Session Lifecycle

> **Phase-3 canonical:** The fixed 9-step progression script below is the canonical current flow and remains unchanged.

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

- `POST /api/sessions/{id}/attempts`
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

## Frontend Responsibilities

The frontend is now responsible for display and input only.

What frontend should do:

1. Start a session with name and condition.
2. Ask backend for the next puzzle (`GET /next-puzzle`).
3. Render the puzzle returned by backend.
4. Submit player answer.
5. Render feedback and completion state from backend fields.

What frontend should not do:

1. Decide next skill.
2. Decide progression order.
3. Decide when a session is complete.

## Frontend Interaction Flow

Simple interaction cycle:

1. No session: show start form.
2. Active session: request next puzzle and render the returned skill screen.
3. Submit answer: show correctness and updated mastery.
4. Request next puzzle again unless backend marks completion.
5. If `session_complete = true`, show completion screen.

This keeps all progression logic in backend services.

## Frontend Maintainability Notes

For student maintainers:

1. Keep store fields aligned with backend contract (`condition`, `currentLevelIndex`, `sessionComplete`).
2. Avoid adding phase-order logic back into components.
3. Keep API client thin and endpoint-focused.
4. Reuse shared puzzle UI wrappers instead of duplicating state logic.
5. Prefer one source of truth: backend progression response fields.

## Alternate Gameplay API (exploratory / gameplay-mode-v2)

> **experimental - gameplay v2:** Additive API path for room/object/inventory interactions. Does not replace the canonical fixed 9-step flow.

### Authority Rules

- Backend is the canonical authority for room/object/inventory/puzzle states.
- Frontend renders server responses and emits actions only.
- Frontend must not make progression decisions or canonical state transitions.

### GET /api/sessions/{id}/game-state

- Purpose: fetch canonical gameplay snapshot for v2 sessions.
- Response must include `interaction_schema_version` and `game_state_version`.
- Server should send `ETag: W/"{session_id}:{game_state_version}"` and support `If-None-Match` for efficient polling.

```json
{
  "ok": true,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 14,
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": [
        { "id": "old_radio", "state": "locked", "revealed": true },
        { "id": "desk_drawer", "state": "unlocked", "revealed": true }
      ]
    },
    "inventory": [
      { "id": "bent_key", "display_name": "Bent Key", "category": "tool" }
    ],
    "dialogue": []
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

### POST /api/sessions/{id}/action

- Purpose: resolve one gameplay action atomically.
- Request supports optional dedupe key `client_action_id`.
- Suggested action types: `inspect`, `collect`, `use_item`, `open_container`, `talk`, `trigger`.

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "6f627d0f-a72f-4a07-984f-dbe9f42c4b15"
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
      "objects": [
        { "id": "old_radio", "state": "unlocked", "revealed": true }
      ]
    },
    "inventory": [
      { "id": "bent_key", "consumed": true }
    ],
    "dialogue": [
      { "id": "radio_unlocked", "text": "The dial clicks into place." }
    ]
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

### Coexistence with POST /api/sessions/{id}/attempts

- `POST /api/sessions/{id}/attempts` remains the canonical learning endpoint.
- When action resolution returns `open_puzzle`, the client should open the puzzle UI and submit answer attempts through `POST /api/sessions/{id}/attempts`.
- BKT and mastery updates remain tied to attempts, not generic room actions.

### Concurrency Guidance

- If an action conflicts with current canonical state, return `409 Conflict`.
- Include machine-readable conflict details and the latest canonical `room_state` in the error envelope.

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": [
        { "id": "old_radio", "state": "unlocked", "revealed": true }
      ]
    }
  },
  "error": {
    "code": "ACTION_CONFLICT",
    "message": "Object state changed before this action was applied."
  },
  "meta": { "interaction_schema_version": 2 }
}
```


<!-- CHANGELOG: pass-2 canonical rewrite preserving Phase-3 flow and gameplay_v2 coexistence details -->

# Session and Gameplay Flow

## Scope

This document defines the canonical runtime flow for Silent Frequency.

It covers:

- the preserved Phase-3 canonical session loop
- the current chapter-based thesis prototype flow
- backend ownership rules
- frontend responsibilities
- additive gameplay v2 flow
- coexistence between room actions, puzzle attempts, and mastery updates
- pre-test, hint, and recovery behavior

> **Current thesis prototype direction:** the primary playable demo is a chapter-based room experience built on gameplay_v2-style interaction, while the preserved Phase-3 flow remains available as a baseline reference for compatibility, testing, and research comparison.

---

## 1. Preserved Phase-3 Baseline Session Lifecycle

This fixed 9-step script remains the preserved baseline progression model used for compatibility, regression testing, and comparison against room-based chapter flow.

It should not be treated as the only user-facing runtime flow for the current thesis prototype.

The backend owns session progression through a fixed 9-step script.

### Progression Script

1. vocabulary, slot 1
2. vocabulary, slot 2
3. vocabulary, slot 3
4. grammar, slot 1
5. grammar, slot 2
6. grammar, slot 3
7. listening, slot 1
8. listening, slot 2
9. listening, slot 3

### Lifecycle Steps

1. Client calls session creation with player name and condition.
2. Backend creates player, game session, initial BKT estimates, and game state.
3. Backend sets `current_level_index = 0`.
4. Client requests the next puzzle using only session ID.
5. Backend resolves skill and slot from `current_level_index`.
6. Backend returns exactly one puzzle variant for that level.
7. Client submits an attempt.
8. Backend scores the answer, updates BKT, logs attempt and event data, and increments `current_level_index`.
9. At level index `9`, backend marks the session complete.

---

## 2. Current Chapter-based Thesis Prototype Flow

The current thesis prototype is centered on a single playable chapter built as a room-based escape experience.

The chapter is structured as:

1. landing page
2. account/login or participant entry
3. story introduction
4. short pre-test
5. chapter entry
6. room and zone exploration
7. gameplay actions and clue gathering
8. puzzle modal opening from room interactions
9. answer submission through canonical attempt endpoint
10. mastery-aware adaptation for later puzzle delivery, hinting, or difficulty
11. chapter completion
12. post-run summary and optional post-test/questionnaire

### Chapter Structure

A chapter may contain multiple connected zones inside one map, for example:

- patient room
- nurse station
- hallway
- security office
- exit area

Not every zone needs to contain a full puzzle. Some zones may exist only for traversal, clue placement, pacing, or narrative transition.

### Runtime Rule

Chapter progression is primarily controlled by:

- canonical room/object/inventory state
- FSM-style gating or world-state preconditions
- puzzle completion results
- backend-owned adaptation state

It is **not** controlled purely by a fixed skill-slot script during the primary gameplay path.

Note: account/login or participant entry is a product-layer onboarding step.

Canonical gameplay and research session tracking still begin at session creation time. Depending on implementation stage, a session may be created either:

- immediately after participant identification, or
- after authenticated account entry and pre-test initialization.

---

## 3. Pre-test and Initialization Flow

Before the player enters the chapter, the system may run a short pre-test.

### Purpose

The pre-test exists to:

- initialize the learner profile
- estimate a starting proficiency band or mastery prior
- support safer first-puzzle selection and hint policy

### Design Guidance

The pre-test should remain short enough to avoid exhausting the player before gameplay begins.

Recommended prototype constraints:

- approximately 15 items maximum
- mixed difficulty
- used for initialization only, not as a standalone proficiency claim

### Runtime Effect

Pre-test output may initialize:

- starting mastery priors
- difficulty band mapping
- first-puzzle tier policy
- early hint assistance level

Finer-grained banding, when used, should map into the runtime-supported gameplay tiers rather than requiring a full parallel content bank for every band.

---

## 4. Chapter Action -> Puzzle -> Update Loop

During chapter gameplay, the canonical runtime loop is:

1. frontend fetches canonical game state
2. player explores one zone of the map
3. player performs a gameplay action
4. backend resolves action and returns typed declarative effects
5. frontend updates UI only from canonical response
6. if an `open_puzzle` effect is returned, frontend opens the puzzle modal
7. player submits the answer through `POST /api/sessions/{session_id}/attempts`
8. backend scores the attempt, updates BKT/mastery, logs telemetry, and returns canonical results
9. frontend renders updated feedback and continues chapter progression

### Important Rule

Gameplay actions and puzzle attempts serve different purposes:

- `POST /action` changes room/object/inventory/dialogue state
- `POST /attempts` remains the canonical learning and mastery update path

## 5. Mastery-aware Adaptation in Chapter Flow

The thesis prototype uses backend-owned adaptive support rather than a fully psychometric CAT implementation.

### Adaptive Inputs

Adaptive decisions may consider:

- current skill mastery estimate
- pre-test initialization result
- recent correctness
- hint usage
- retry count
- puzzle availability within current chapter state

### Adaptive Outputs

The backend may adapt:

- puzzle difficulty tier
- hint disclosure timing
- follow-up puzzle variant choice
- pacing of challenge escalation

### Constraint

Adaptive logic must remain compatible with chapter gating.

The backend must not select a puzzle that violates current room/FSM/world-state constraints, even if that puzzle would otherwise match the preferred skill or tier.

## 6. Canonical API Flow

The examples below describe the minimal canonical session API.

In product UX, session creation may occur after participant entry, account login, or pre-test initialization, depending on the current prototype implementation.

### Session Start

- `POST /api/sessions`
- Minimal baseline input includes: `display_name`, `condition`
- Product-facing flows may derive these values after participant entry or authenticated onboarding
- Output includes: `condition`, `current_level_index`
- `mode` may be included when gameplay v2 support is enabled

Example request:

```json
{
  "display_name": "Player One",
  "condition": "adaptive"
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "session_id": "4dc9c5f2-8fdb-45f2-9f31-0a6b4f87a111",
    "condition": "adaptive",
    "current_level_index": 0,
    "mastery": {
      "vocabulary": { "p_learned": 0.25, "update_count": 0 },
      "grammar": { "p_learned": 0.25, "update_count": 0 },
      "listening": { "p_learned": 0.25, "update_count": 0 }
    }
  },
  "error": null,
  "meta": {}
}
```

### Get Next Puzzle

- `GET /api/sessions/{session_id}/next-puzzle`
- No skill query is required
- Backend decides skill, slot, tier, and variant
- Response includes `slot_order` and `session_complete`

Example response:

```json
{
  "ok": true,
  "data": {
    "puzzle_id": "vocabulary_01",
    "variant_id": "vocabulary_01_mid",
    "skill": "vocabulary",
    "slot_order": 1,
    "difficulty_tier": "mid",
    "session_complete": false
  },
  "error": null,
  "meta": {}
}
```

### Submit Attempt

- `POST /api/sessions/{session_id}/attempts`
- Backend updates BKT and session progression
- Response includes `current_level_index` and `session_complete`

Example request:

```json
{
  "variant_id": "vocabulary_01_mid",
  "answer": "example",
  "response_time_ms": 2200,
  "hint_count_used": 0
}
```

Example response:

```json
{
  "ok": true,
  "data": {
    "is_correct": true,
    "correct_answers": ["example"],
    "p_learned_before": 0.25,
    "p_learned_after": 0.41,
    "current_level_index": 1,
    "session_complete": false
  },
  "error": null,
  "meta": {}
}
```

---

## 7. Backend Ownership Rules

Backend ownership means:

1. client does not decide canonical puzzle progression
2. backend controls skill/slot progression in the preserved Phase-3 baseline
3. backend controls gated puzzle availability in chapter-based gameplay flow
4. backend controls completion state
5. session condition is stored server-side and used for tier or support policy
6. backend remains authoritative for scoring, BKT, and progression

### Difficulty Policy

1. Slot 1 is always `mid`
2. If condition is `static`, all slots use `mid`
3. If condition is `adaptive`, slots 2 and 3 use BKT-based tier selection

### Data Flow

Core session state fields:

- `condition`
- `current_level_index`

How they move:

1. created in session service at session start
2. read in puzzle selection for level resolution
3. updated in attempt submission after each answer
4. used to determine `session_complete`

### Logging Touched by Canonical Flow

1. `attempt_submitted` event remains canonical
2. `session_progressed` is written after level advancement
3. attempt rows still record answer quality and timing

---

## 8. Frontend Responsibilities

The frontend is responsible for display and input only.

### Frontend Should

1. start a session with name and condition
2. request the next puzzle
3. render the returned puzzle
4. submit the player answer
5. render correctness, mastery, and completion state from backend fields

### Frontend Must Not

1. decide the next skill
2. decide progression order
3. decide when a session is complete
4. compute correctness or mastery updates
5. infer adaptive difficulty rules locally

### Frontend Interaction Flow

1. no session: show start form
2. active session: request next puzzle and render returned skill screen
3. submit answer: show correctness and updated mastery
4. request next puzzle again unless backend marks completion
5. if `session_complete = true`, show completion screen

---

## 9. Gameplay v2 Overview

> **experimental — gameplay v2:** Additive API and content path for room, object, inventory, and dialogue interactions. It does not replace the canonical fixed 9-step learning flow.

Gameplay v2 introduces:

- room and object interactions
- inventory state
- typed action payloads
- declarative `effects[]`
- canonical game-state snapshots
- stale-state conflict handling
- telemetry for gameplay actions

### Authority Rules

- Backend is the canonical authority for room, object, inventory, and puzzle states.
- Frontend renders server responses and emits actions only.
- Frontend must not make progression decisions or canonical gameplay state transitions.
- `session.mode` must be set at session creation and remain immutable for the full session.
- Server must enforce `session.mode == gameplay_v2` and `GAMEPLAY_V2_ENABLED=true` before serving gameplay v2 endpoints.

Recommended mode-gate failure:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "MODE_MISMATCH",
    "message": "Session mode is not gameplay_v2 or v2 is disabled"
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

---

## 10. Gameplay v2 Endpoints in Runtime Flow

### `GET /api/sessions/{session_id}/game-state`

Purpose:

- fetch canonical gameplay snapshot for gameplay v2 sessions

Response must include:

- `interaction_schema_version`
- `game_state_version`
- `updated_at`
- `room_state`
- `inventory`
- `dialogue_queue`

Inventory item shape must be identical across `GET /game-state` and `POST /action` responses.

Recommended response:

```json
{
  "ok": true,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 42,
    "updated_at": "2026-03-21T12:00:00Z",
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    },
    "inventory": [
      {
        "id": "k1",
        "display_name": "Silver Key",
        "category": "tool",
        "consumed": false
      }
    ],
    "dialogue_queue": []
  },
  "error": null,
  "meta": {
    "interaction_schema_version": 2
  }
}
```

Recommended header:

```text
ETag: W/"<session_id>:<game_state_version>"
```

### `POST /api/sessions/{session_id}/action`

Purpose:

- resolve one gameplay action atomically

Request supports:

- `client_action_id` for dedupe
- `client_game_state_version` for optimistic concurrency detection

Suggested action types:

- `inspect`
- `collect`
- `use_item`
- `open_container`
- `talk`
- `trigger`

Example request:

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "safe_01",
  "item_id": "screwdriver_01",
  "client_action_id": "uuid-123e4567-e89b-12d3-a456-426614174000",
  "client_game_state_version": 41
}
```

Success example:

```json
{
  "ok": true,
  "data": {
    "effects": [
      { "type": "unlock", "target_id": "safe_01" },
      { "type": "open_puzzle", "payload": { "puzzle_id": "p_safe_01" } }
    ],
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    },
    "inventory": [
      {
        "id": "k1",
        "display_name": "Silver Key",
        "category": "tool",
        "consumed": false
      }
    ],
    "dialogue_queue": [],
    "game_state_version": 42,
    "updated_at": "2026-03-21T12:01:00Z"
  },
  "error": null,
  "meta": {
    "interaction_schema_version": 2
  }
}
```

---

## 11. Conflict and Concurrency Behavior

If an action conflicts with current canonical state, the server should return `409 Conflict` and include the latest canonical snapshot needed for UI recovery.

### Stale-state example

```json
{
  "ok": false,
  "error": {
    "code": "CONFLICT_STALE_STATE",
    "message": "Client game_state_version is stale"
  },
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    },
    "game_state_version": 42
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

### Conflict example

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": [
        {
          "id": "old_radio",
          "state": "unlocked",
          "revealed": true
        }
      ]
    }
  },
  "error": {
    "code": "ACTION_CONFLICT",
    "message": "Object state changed before this action was applied."
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

### Client Behavior on `409`

Frontend should:

1. refetch `GET /game-state`
2. reconcile UI to server snapshot
3. show a non-blocking banner such as `State refreshed`
4. allow retry
5. avoid applying hidden optimistic canonical mutations

---

## 12. Dedupe and Idempotency

- Server should dedupe by `(session_id, client_action_id)` when `client_action_id` is present.
- Recommended behavior:
  - return the previous successful `200` response for confirmed duplicates, or
  - return `409` with canonical state when replay certainty cannot be guaranteed

### Safe duplicate replay example

```json
{
  "ok": true,
  "data": {
    "effects": [{ "type": "unlock", "target_id": "old_radio" }],
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    },
    "inventory": [],
    "dialogue_queue": [],
    "game_state_version": 22
  },
  "error": null,
  "meta": {
    "interaction_schema_version": 2
  }
}
```

### Uncertain duplicate example

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": []
    }
  },
  "error": {
    "code": "DUPLICATE_ACTION_UNCERTAIN",
    "message": "Duplicate request detected, but previous commit status is uncertain."
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

---

## 13. Coexistence with Canonical Attempts

`POST /api/sessions/{session_id}/attempts` remains the canonical learning endpoint.

When action resolution returns `open_puzzle`:

1. frontend opens the puzzle UI
2. answer attempts are still submitted through `POST /api/sessions/{session_id}/attempts`
3. BKT and mastery updates remain tied to attempts, not generic room actions

This rule preserves comparability across Phase-3 and gameplay v2 sessions.

---

## 14. Auto-hint Policy

Auto-hint policy is backend-configurable and must not be inferred client-side.

Suggested configuration:

```json
{
  "idle_seconds": 45,
  "failed_attempts_threshold": 2
}
```

For chapter-based prototype flow, hint policy may also vary by chapter state.

Early tutorial states may allow more guided support, while later states should gradually reduce direct guidance and require stronger player-driven problem solving.

Required telemetry event for hint disclosure:

```json
{
  "event_type": "hint_opened",
  "payload": {
    "session_id": "4dc9c5f2-8fdb-45f2-9f31-0a6b4f87a111",
    "hint_type": "auto",
    "hint_id": "radio_hint_01",
    "timestamp": "2026-03-21T10:24:00Z"
  }
}
```

---

## 15. Maintenance Notes

For student maintainers:

1. keep progression decisions in backend services, not frontend phase state
2. do not bypass `current_level_index` when adding or debugging routes
3. if level count changes, update the level script in one place and verify completion logic
4. keep static and adaptive behavior simple and explicit
5. preserve BKT engine isolation
6. validate API contract changes with backend schemas and frontend types together
7. treat gameplay v2 as additive, not as a silent rewrite of canonical flow

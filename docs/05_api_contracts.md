<!-- CHANGELOG: pass-2 canonical rewrite preserving detailed request/response and error examples -->

# API Contracts

## Scope

This document defines the canonical HTTP contracts for Silent Frequency.

It includes:

- canonical response envelope
- session endpoints
- gameplay v2 endpoints
- error mapping
- conflict semantics
- versioning notes
- change management checklist

---

## 1. Canonical Response Envelope

All public endpoints should preserve the canonical envelope shape:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

Canonical failure shape:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "SOME_ERROR_CODE",
    "message": "Human-readable explanation"
  },
  "meta": {}
}
```

For gameplay v2 responses, `meta` should usually include:

```json
{
  "interaction_schema_version": 2
}
```

---

## 2. `POST /api/sessions`

Creates a new session.

### Canonical Request

```json
{
  "display_name": "Player One",
  "condition": "adaptive"
}
```

### Gameplay v2-capable Request

```json
{
  "display_name": "Player One",
  "condition": "adaptive",
  "mode": "gameplay_v2"
}
```

### Response Example

```json
{
  "ok": true,
  "data": {
    "session_id": "4dc9c5f2-8fdb-45f2-9f31-0a6b4f87a111",
    "condition": "adaptive",
    "current_level_index": 0,
    "mastery": {
      "vocabulary": {
        "p_learned": 0.25,
        "update_count": 0
      },
      "grammar": {
        "p_learned": 0.25,
        "update_count": 0
      },
      "listening": {
        "p_learned": 0.25,
        "update_count": 0
      }
    }
  },
  "error": null,
  "meta": {}
}
```

### Notes

- `mode` may be optional depending on current server defaults
- session mode should be immutable after creation for research integrity
- mode-aware clients must not assume gameplay v2 is globally enabled

---

## 3. `GET /api/sessions/{session_id}/next-puzzle`

Returns the next puzzle according to backend-owned progression.

### Canonical Response Example

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

### Batch-2 / interaction-capable Response Example

For additive Phase-3 interaction metadata:

```json
{
  "ok": true,
  "data": {
    "puzzle_id": "start_vocab_sign",
    "variant_id": "start_vocab_sign_mid",
    "skill": "vocabulary",
    "slot_order": 1,
    "difficulty_tier": "mid",
    "interaction_mode": "scene_hotspot",
    "interaction": {
      "prompts": {
        "p1": "Translate the warning sign."
      },
      "hotspots": [
        {
          "hotspot_id": "sign_1",
          "shape": {
            "kind": "rect",
            "x": 0.12,
            "y": 0.24,
            "w": 0.16,
            "h": 0.21
          },
          "trigger": { "prompt_ref": "p1" }
        }
      ]
    },
    "session_complete": false
  },
  "error": null,
  "meta": {}
}
```

### Contract Rules

- existing fields must remain backward compatible
- additive fields such as `interaction_mode` and `interaction` must not break plain puzzles
- existing clients may ignore additive interaction fields

---

## 4. `POST /api/sessions/{session_id}/attempts`

Submits one answer attempt.

### Canonical Request Example

```json
{
  "variant_id": "vocabulary_01_mid",
  "answer": "sample answer",
  "response_time_ms": 2200,
  "hint_count_used": 0
}
```

### Interaction-trace-capable Request Example

```json
{
  "variant_id": "start_listen_code_mid",
  "answer": "sample answer",
  "response_time_ms": 1500,
  "hint_count_used": 1,
  "interaction_trace": [
    {
      "event_type": "hotspot_clicked",
      "hotspot_id": "old_radio",
      "elapsed_ms": 120
    },
    {
      "event_type": "hint_opened",
      "hint_id": "hint_01",
      "elapsed_ms": 820
    }
  ],
  "metadata": {
    "source": "gameplay_v2"
  }
}
```

### Canonical Response Example

```json
{
  "ok": true,
  "data": {
    "is_correct": true,
    "correct_answers": ["sample answer"],
    "p_learned_before": 0.25,
    "p_learned_after": 0.41,
    "current_level_index": 1,
    "session_complete": false
  },
  "error": null,
  "meta": {}
}
```

### Contract Rules

- `interaction_trace` is optional
- requests without `interaction_trace` remain valid
- scoring behavior must remain unchanged
- `metadata.source = "gameplay_v2"` is telemetry context only and must not alter scoring, BKT, or progression

---

## 5. `GET /api/sessions/{session_id}/game-state`

Gameplay v2 endpoint for fetching the canonical gameplay snapshot.

### Required Response Fields

- `interaction_schema_version`
- `game_state_version`
- `updated_at`
- `room_state`
- `inventory`
- `dialogue_queue`

### Response Example

```json
{
  "ok": true,
  "data": {
    "interaction_schema_version": 2,
    "game_state_version": 42,
    "updated_at": "2026-03-21T12:00:00Z",
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

### Header Semantics

Recommended header:

```text
ETag: W/"<session_id>:<game_state_version>"
```

Clients may send `If-None-Match`. The server may respond `304 Not Modified` when unchanged.

---

## 6. `POST /api/sessions/{session_id}/action`

Gameplay v2 endpoint for resolving one typed gameplay action.

### Required Request Fields

- `interaction_schema_version`
- `action`
- `target_id`

### Optional Request Fields

- `item_id`
- `client_action_id`
- `client_game_state_version`
- `client_ts`

### Request Example

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

### Success Response Example

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
  "meta": {
    "interaction_schema_version": 2
  }
}
```

### Effect Rules

- `effects[]` must be declarative only
- no executable scripts
- no dynamic client-side rule execution
- canonical mutations happen server-side before response is returned

---

## 7. Conflict Semantics

### Stale-state `409`

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
  "meta": {
    "interaction_schema_version": 2
  }
}
```

### Generic conflict `409`

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "objects": [{ "id": "old_radio", "state": "unlocked", "revealed": true }]
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

Client behavior:

1. refetch canonical game state
2. reconcile UI to server snapshot
3. avoid applying local optimistic canonical state changes
4. allow retry

---

## 8. Dedupe Semantics

Dedupe scope should be `(session_id, client_action_id)`.

### Confirmed duplicate replay

The server may return the original successful `200` response.

### Uncertain duplicate replay

The server may return a `409` when replay safety cannot be guaranteed.

Example:

```json
{
  "ok": false,
  "data": {
    "room_state": {
      "room_id": "radio_room_v2",
      "scene_asset_key": "scene_radio_room_v2",
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

## 9. Error Envelope and HTTP Mapping

Recommended failure envelope:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "INVALID_ACTION",
    "message": "Unsupported action for target_id=old_radio."
  },
  "meta": {
    "interaction_schema_version": 2
  }
}
```

Recommended mapping:

- `400` invalid payload, unsupported action, or schema mismatch
- `403` authenticated but not allowed to mutate this session, including `MODE_MISMATCH`
- `404` session or target object not found
- `409` stale state or action conflict
- `500` unexpected server error

---

## 10. Versioning Rules

### Phase-3

- canonical session flow uses `GET /next-puzzle` and `POST /attempts`
- additive interaction metadata may appear in puzzle responses without changing endpoint identity

### Gameplay v2

- all contracts must include `interaction_schema_version: 2`
- mode selection must happen at session creation
- migration should be by session/config mode, not by silently overloading one client path

---

## 11. Contract Change Checklist

Whenever an API contract changes:

1. update this file
2. update backend schemas
3. update backend route/service tests
4. update frontend `src/lib/api.ts`
5. update frontend `src/lib/types.ts`
6. update relevant component and integration tests
7. update any E2E, telemetry, and runbook instructions affected by the change

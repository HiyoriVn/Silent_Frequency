# API Contracts

## Canonical Response Envelope

All endpoints should preserve the canonical envelope shape:

```json
{
  "ok": true,
  "data": {},
  "error": null,
  "meta": {}
}
```

## Session Endpoints

### `POST /api/sessions`

Creates a new session.

Example request:

```json
{
  "display_name": "Player One",
  "condition": "adaptive",
  "mode": "phase3"
}
```

Notes:

- `mode` may be optional depending on current server defaults
- supported modes must be documented centrally

### `GET /api/sessions/{session_id}/next-puzzle`

Returns the next puzzle according to backend-owned progression.

Expected response fields include:

- `puzzle_id`
- `variant_id`
- `skill`
- `slot_order`
- `session_complete`

### `POST /api/sessions/{session_id}/attempts`

Submits one answer attempt.

Example request:

```json
{
  "variant_id": "vocabulary_01_mid",
  "answer": "example",
  "response_time_ms": 2100,
  "hint_count_used": 0
}
```

Expected response fields include:

- correctness result
- mastery information
- `current_level_index`
- `session_complete`

## Gameplay v2 Endpoints

### `GET /api/sessions/{session_id}/game-state`

Returns the canonical gameplay snapshot for gameplay v2 sessions.

Expected fields:

- `interaction_schema_version`
- `game_state_version`
- `updated_at`
- `room_state`
- `inventory`
- `dialogue_queue`

### `POST /api/sessions/{session_id}/action`

Resolves one gameplay action.

Example request:

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "uuid-123",
  "client_game_state_version": 41
}
```

Success responses must return declarative `effects[]` only.

Conflict responses should return `409` with machine-readable conflict metadata and the latest canonical snapshot needed for UI recovery.

## Error Mapping

Recommended HTTP mapping:

- `400` invalid payload, unsupported action, or schema mismatch
- `403` mode mismatch or feature disabled
- `404` session or target not found
- `409` stale state or action conflict
- `500` unexpected server error

## Contract Change Checklist

Whenever an API contract changes:

1. update this file
2. update backend schemas
3. update frontend `src/lib/api.ts`
4. update frontend `src/lib/types.ts`
5. update relevant tests
6. update E2E or runbook instructions affected by the change

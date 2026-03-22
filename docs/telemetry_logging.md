# Telemetry Logging Policy (Batch 4.3)

## Scope

This document defines canonical telemetry event contracts for gameplay v2 and Phase-3-compatible pipelines.
Telemetry is observational and must never alter scoring, BKT, progression, or completion decisions.

## Canonical Event Types

### `game_action`

Purpose: log every resolved gameplay v2 action.

Example payload:

```json
{
  "version": 1,
  "type": "game_action",
  "session_id": "0ef2e0f5-6851-4302-aab4-21443f30f61f",
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "e9696354-f7cc-463f-9e5f-fe39a7fd8bf0",
  "timestamp": "2026-03-22T08:00:00Z",
  "resulting_effects": [
    { "type": "unlock", "target_id": "old_radio" },
    { "type": "open_puzzle", "target_id": "start_listen_code" }
  ]
}
```

Rules:

- `resulting_effects` must be minimal: only `type` and `target_id`.
- Do not emit full canonical room snapshots in `game_action` events.
- If payload size is large, server trims with warning logging and increments metrics.

### `puzzle_interaction_trace`

Purpose: observational UX trace from actions/attempts; never authoritative.

Example payload:

```json
{
  "version": 1,
  "type": "interaction_trace",
  "puzzle_id": "start_listen_code",
  "variant_id": "start_listen_code_mid",
  "trace": [
    {
      "event_type": "hotspot_clicked",
      "hotspot_id": "old_radio",
      "elapsed_ms": 120
    },
    { "event_type": "hint_opened", "hint_id": "hint_01", "elapsed_ms": 820 }
  ],
  "response_time_ms": 1420,
  "_truncated": false
}
```

Trace rules:

- max events per trace: 20
- per-event serialized size: <= 10KB
- if trace is trimmed by count or size, service sets `_truncated: true`
- trimming increments metrics (`telemetry.trace.truncated` and/or `telemetry.trace.too_large`)

### `attempt_submitted`

Purpose: canonical scoring submission record from attempt pipeline.

Example payload:

```json
{
  "version": 1,
  "type": "attempt_submitted",
  "session_id": "0ef2e0f5-6851-4302-aab4-21443f30f61f",
  "variant_id": "start_listen_code_mid",
  "is_correct": true,
  "response_time_ms": 3110,
  "hint_count_used": 0,
  "timestamp": "2026-03-22T08:05:00Z"
}
```

## `_http_status` Convenience Field

`_http_status` is an internal convenience helper when included in body metadata. HTTP status code and headers are authoritative.
Frontend may read `_http_status` for convenience, but must prefer status code and headers from the HTTP response.

## Retention and Privacy

- default raw event retention: 90 days
- exports must anonymize participant identity and include `participant_code` only
- deletion policy must support participant data deletion requests via project support/admin channel

## Metrics Expectations

The service emits lightweight counters for operations visibility:

- `telemetry.game_action.count`
- `telemetry.trace.truncated`
- `telemetry.trace.too_large`

These counters are currently in-process stubs and can be wired to real metrics backends later.

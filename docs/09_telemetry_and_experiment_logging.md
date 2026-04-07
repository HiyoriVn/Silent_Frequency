<!-- CHANGELOG: pass-2 canonical rewrite preserving telemetry payload examples, limits, retention, and QA thresholds -->

# Telemetry and Experiment Logging

## Scope

This document defines canonical telemetry event contracts for gameplay v2 and Phase-3-compatible pipelines.

Telemetry is observational and must never alter:

- scoring
- BKT updates
- progression
- completion decisions

---

## 1. Canonical Event Types

### `game_action`

Purpose:

- log every resolved gameplay v2 action

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

- `resulting_effects` must be minimal
- include only fields needed for effect interpretation such as `type` and `target_id`
- do not emit full canonical room snapshots inside `game_action`
- if payload size becomes large, trim safely and increment metrics

---

### `puzzle_interaction_trace`

Purpose:

- observational UX trace from puzzle actions or attempts
- never authoritative for gameplay, scoring, or progression

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
    {
      "event_type": "hint_opened",
      "hint_id": "hint_01",
      "elapsed_ms": 820
    }
  ],
  "response_time_ms": 1420,
  "_truncated": false
}
```

Trace rules:

- max events per trace: `20`
- per-event serialized size: `<= 10KB`
- if trace is trimmed by count or size, payload must include `_truncated: true`
- trimming increments:
  - `telemetry.trace.truncated`
  - `telemetry.trace.too_large` when applicable

---

### `attempt_submitted`

Purpose:

- canonical scoring submission record from the attempt pipeline

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
  "metadata": { "source": "gameplay_v2" },
  "timestamp": "2026-03-22T08:05:00Z"
}
```

Rules:

- for gameplay v2 modal submissions, clients should send `metadata.source = "gameplay_v2"`
- metadata is telemetry context only
- metadata must not alter scoring, BKT, progression, or tier policy
- server-side QA should verify `metadata.source` coverage for gameplay v2 attempt traffic

---

## 2. Observational-only Rule

Telemetry must never affect:

1. answer scoring
2. BKT updates
3. `current_level_index`
4. session completion
5. adaptive difficulty policy
6. object or inventory state transitions

Telemetry is for debugging, analysis, and research support only.

---

## 3. `_http_status` Convenience Field

`_http_status` is an internal convenience helper when included in metadata.

HTTP status code and headers remain authoritative.

Frontend may read `_http_status` for convenience, but should prefer the actual status code and headers from the HTTP response.

---

## 4. Retention and Privacy

Recommended policy:

- default raw event retention: 90 days
- exports should anonymize participant identity
- exports should use `participant_code` or equivalent pseudonymous identifiers
- deletion policy must support participant data deletion requests through the project support/admin path

---

## 5. Metrics Expectations

The service should expose lightweight counters for operational visibility:

- `telemetry.game_action.count`
- `telemetry.trace.truncated`
- `telemetry.trace.too_large`

These may begin as in-process counters and later be wired to a fuller metrics backend.

---

## 6. Batch 4.5 QA Thresholds

During gameplay v2 pilot validation:

- `telemetry.trace.truncated` should remain below `5%` of total interaction-trace events
- `telemetry.trace.too_large` should remain `0`
- `attempt_submitted` telemetry for gameplay v2 should include `metadata.source="gameplay_v2"`

---

## 7. Research Use Guidance

Telemetry is useful for:

- flow completion analysis
- interaction pattern observation
- hint usage analysis
- stale-state conflict recovery analysis
- comparing adaptive and static conditions
- mapping gameplay actions to canonical learning attempts

Telemetry is not sufficient on its own to justify learning claims.

Any research conclusion should be tied to:

- explicit evaluation design
- canonical attempt data
- known feature-flag state
- stated limitations and threats to validity

# Gameplay v2 Pilot Plan (Batch 4.5)

## Objective

Validate gameplay_v2 integration quality with production-like telemetry and attempt flows, while preserving backend-authoritative scoring/BKT behavior.

## Pilot Scope

- Participants: 5 internal users
- Duration: 48 hours
- Sessions: 1 session per participant
- Mode: `gameplay_v2`

## Execution Steps

1. Enable gameplay_v2 in staging:
   - `export GAMEPLAY_V2_ENABLED=true`
2. Verify backend is reachable and seeded.
3. For each participant:
   - Create a new gameplay_v2 session.
   - Complete at least one room action path that opens a puzzle modal.
   - Submit at least one puzzle attempt from modal flow.
4. Collect logs and metrics after each day and at end of pilot.

## What To Monitor

### Telemetry Volume and Integrity

- `game_action` events are emitted for resolved room actions.
- `puzzle_interaction_trace` events appear for action/attempt trace submissions.
- `attempt_submitted` telemetry includes `metadata.source = "gameplay_v2"` for gameplay_v2 modal attempts.

### Trace Quality Thresholds

- `telemetry.trace.truncated` < 5% of total interaction-trace events.
- `telemetry.trace.too_large` == 0.
- Trace event count per payload <= 20 after server processing.

### Functional Correctness

- 409 stale-state path shows retry UX and re-fetches canonical state.
- Attempt submission still follows canonical backend scoring and BKT update path.
- No regressions in Phase-3 endpoints.

## Data Collection

- Query `event_log` grouped by `event_type` and session.
- Query `attempts` rows for pilot sessions.
- Snapshot metrics counters:
  - `telemetry.game_action.count`
  - `telemetry.trace.truncated`
  - `telemetry.trace.too_large`

## Exit Criteria

- All targeted backend/frontend integration tests pass.
- Functional QA checklist completed.
- Metrics thresholds met.
- No critical regressions in scoring/BKT/Phase-3 workflows.

## Rollback Trigger

Immediately disable gameplay_v2 if any of the following occur:

- repeated 409 loops with unusable recovery UX,
- malformed trace payload growth or `telemetry.trace.too_large > 0`,
- attempt pipeline instability affecting canonical scoring.

Rollback action:

1. Set `GAMEPLAY_V2_ENABLED=false`.
2. Keep Phase-3 endpoints active.
3. Capture diagnostics and event samples.
4. Resume pilot only after fixes and re-validation.

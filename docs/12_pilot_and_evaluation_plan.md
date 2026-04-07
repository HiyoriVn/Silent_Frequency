<!-- CHANGELOG: pass-2 canonical rewrite preserving gameplay_v2 pilot scope, metrics, thresholds, and rollback criteria -->

# Pilot and Evaluation Plan

## Scope

This document defines pilot readiness and evaluation guidance for Silent Frequency, with special attention to gameplay v2 validation.

It is intended for:

- controlled internal pilots
- pre-thesis validation
- staging rollout checks
- early evaluation planning

---

## 1. Pilot Goal

The pilot validates that Silent Frequency is stable enough for controlled use and that core evaluation signals can be collected reliably.

For gameplay_v2 specifically, the pilot should confirm that room-based interactions can coexist with canonical attempt scoring and telemetry without breaking backend authority.

---

## 2. Gameplay v2 Pilot Baseline

### Suggested Initial Scope

- participants: 5 internal users
- duration: 48 hours
- sessions: 1 session per participant
- mode: `gameplay_v2`

This should remain a deliberately small pilot before broader rollout.

---

## 3. Pilot Objectives

The pilot should confirm:

- sessions can complete without major flow errors
- adaptive and static conditions behave as intended
- gameplay v2 interactions are safe when enabled
- telemetry is present and interpretable
- participants can complete the experience without critical UX blockers
- canonical attempt scoring and BKT behavior remain intact

---

## 4. Entry Criteria

Before pilot start:

- backend and frontend critical tests pass
- seed data is validated
- required migrations are applied
- feature-flag settings are documented
- E2E manual flow is verified
- telemetry emission is confirmed
- gameplay_v2 mode creation works
- rollback path is verified

---

## 5. Pilot Execution Steps

1. enable gameplay_v2 in staging:

```bash
export GAMEPLAY_V2_ENABLED=true
```

2. verify backend is reachable and correctly seeded
3. for each participant:
   - create a new gameplay_v2 session
   - complete at least one room action path that opens a puzzle modal
   - submit at least one puzzle attempt from modal flow

4. collect logs and metrics after each day and at the end of the pilot

---

## 6. What to Monitor

### Telemetry Volume and Integrity

- `game_action` events are emitted for resolved room actions
- `puzzle_interaction_trace` events appear for action or attempt trace submissions
- `attempt_submitted` telemetry includes `metadata.source = "gameplay_v2"` for gameplay_v2 modal attempts

### Trace Quality Thresholds

- `telemetry.trace.truncated` < 5% of total interaction-trace events
- `telemetry.trace.too_large` == 0
- trace event count per payload <= 20 after server processing

### Functional Correctness

- stale-state `409` path shows retry UX and re-fetches canonical state
- attempt submission still follows canonical backend scoring and BKT update path
- no regressions in Phase-3 endpoints
- duplicate action behavior is safe when `client_action_id` is present

### UX and Flow Quality

- players can understand what to do next
- puzzle modal opens reliably from gameplay effects
- inventory and dialogue behavior are understandable
- no major dead-end states block progress without recovery

---

## 7. Data Collection During Pilot

Collect at minimum:

- event log grouped by event type and session
- attempt rows for pilot sessions
- metrics counter snapshots:
  - `telemetry.game_action.count`
  - `telemetry.trace.truncated`
  - `telemetry.trace.too_large`

- participant notes about confusion, delay, or blockers
- basic completion and progression outcome summaries

For gameplay_v2 analysis, also consider:

- action diversity
- time-to-first-hint
- number of stale-state conflicts
- time from `open_puzzle` effect to attempt submission

---

## 8. Success Metrics

Suggested success metrics:

- session completion rate
- average attempts per puzzle
- hint usage distribution
- conflict recovery rate for gameplay_v2
- telemetry completeness
- trace truncation rate
- user-reported confusion points
- absence of regression in canonical Phase-3 scoring flow

---

## 9. Failure Triggers

Pause or revert if any of the following occur:

- session completion breaks
- attempts fail to update mastery correctly
- telemetry is missing or malformed
- conflict handling causes broken UI recovery
- gameplay_v2 negatively affects canonical attempt flow
- repeated `409` loops lead to unusable recovery UX
- `telemetry.trace.too_large > 0`
- malformed or unbounded trace payload growth appears

---

## 10. Exit Criteria

Pilot exit criteria:

- targeted backend and frontend integration tests pass
- functional QA checklist is completed
- telemetry thresholds are met
- no critical regressions exist in scoring, BKT, or canonical Phase-3 workflows
- collected data is sufficiently complete for post-pilot review

---

## 11. Rollback Trigger and Response

Immediately disable gameplay_v2 if any critical trigger occurs.

### Rollback Action

1. set `GAMEPLAY_V2_ENABLED=false`
2. keep Phase-3 endpoints active
3. capture diagnostics and representative event samples
4. resume pilot only after fixes and re-validation

### Operational Principle

Rollback should preserve canonical behavior and avoid contaminating later analysis with unstable sessions.

---

## 12. Post-pilot Review

After pilot completion:

1. summarize system stability
2. summarize telemetry quality
3. identify content or UX bottlenecks
4. review threats to validity
5. classify issues by severity
6. decide whether to proceed, revise, narrow scope, or pause

Recommended outputs:

- pilot summary note
- telemetry quality summary
- incident list
- decision memo for next rollout step

---

## 13. Rollout Recommendation

Recommended sequence:

1. keep gameplay_v2 disabled by default
2. enable for internal QA sessions only
3. run a small internal pilot
4. segment dashboards and analysis by mode
5. expand only after conflict, telemetry, and scoring stability are confirmed

Broader rollout should happen only after the small pilot demonstrates stable behavior and clean data collection.

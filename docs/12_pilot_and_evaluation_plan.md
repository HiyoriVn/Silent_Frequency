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

For the current thesis prototype, the pilot should specifically confirm that:

- a single room-based chapter can be completed without major flow failures
- chapter interactions and puzzle gating remain understandable
- adaptive support can coexist with canonical attempt scoring and BKT updates
- pre-test, chapter gameplay, and post-run data can be collected consistently
- telemetry and attempt data are reliable enough for thesis-scale analysis

Educational-support findings from this pilot should be treated as exploratory prototype evidence, not as formal proficiency measurement results.

---

## 2. Thesis Prototype Pilot Baseline

### Suggested Initial Scope

- participants: small controlled pilot group
- target scale: 5 to 10 users for internal or pre-thesis validation
- sessions: 1 session per participant
- primary mode: chapter-based gameplay_v2 prototype
- chapter scope: one playable chapter only

This should remain a deliberately small pilot before any broader rollout or stronger research claims.

---

## 3. Pilot Objectives

The pilot should confirm:

- sessions can complete without major flow errors
- adaptive and static conditions behave as intended
- gameplay v2 interactions are safe when enabled
- telemetry is present and interpretable
- participants can complete the experience without critical UX blockers
- canonical attempt scoring and BKT behavior remain intact

The pilot should also confirm:

- pre-test initialization completes without major friction
- players can understand what to do next inside the chapter
- zone transitions do not create confusion or accidental dead ends
- puzzle modal flow feels connected to room exploration rather than detached from it
- hint and support systems are understandable and not overly intrusive

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
   - create or register the participant profile as required
   - complete the pre-test or initialization flow
   - enter the playable chapter
   - complete at least one meaningful room-action path that opens a puzzle modal
   - submit puzzle attempts through the canonical attempt path
   - reach chapter completion when possible
   - complete post-run questionnaire or post-test if included

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

### Chapter Flow Quality

- time to complete pre-test
- time to first meaningful interaction
- time to first puzzle modal
- chapter completion rate
- number of dead-end actions or confusion points
- number of hint requests before first successful puzzle
- whether players understand zone progression and object affordances

### Educational-support Signals

- distribution of pre-test initialization bands
- puzzle correctness patterns across the chapter
- hint usage by puzzle or zone
- vocabulary board or journal access behavior where tracked
- post-run perceived learning or confidence feedback

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
- chapter build or content revision identifier

---

## 8. Success Metrics

Suggested success metrics:

- chapter completion rate
- average attempts per puzzle
- hint usage distribution
- time to first puzzle completion
- number of critical confusion points reported
- conflict recovery rate for gameplay_v2
- telemetry completeness
- trace truncation rate
- user-reported clarity, engagement, and perceived support quality
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
- players consistently fail to understand chapter goals
- room interactions repeatedly lead to dead ends without recovery
- puzzle modal flow feels detached from room gameplay
- pre-test causes excessive fatigue before gameplay
- chapter completion becomes too rare to support pilot analysis

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
3. identify chapter content, zone, or UX bottlenecks
4. review threats to validity
5. classify issues by severity
6. decide whether to proceed, revise, narrow scope, or pause

Recommended outputs:

- pilot summary note
- chapter flow review
- telemetry quality summary
- incident list
- decision memo for next revision step

---

## 13. Rollout Recommendation

Recommended sequence:

1. keep gameplay_v2 disabled by default
2. enable for internal QA sessions only
3. run a small internal pilot
4. segment dashboards and analysis by mode
5. expand only after conflict, telemetry, and scoring stability are confirmed

Broader rollout should happen only after the small pilot demonstrates stable behavior and clean data collection.

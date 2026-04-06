# Pilot and Evaluation Plan

## Goal

The pilot validates that Silent Frequency is stable enough for controlled use and that core evaluation signals can be collected reliably.

## Pilot Objectives

The pilot should confirm:

- sessions can complete without major flow errors
- adaptive and static conditions behave as intended
- gameplay v2 interactions are safe when enabled
- telemetry is present and interpretable
- participants can complete the experience without critical UX blockers

## Entry Criteria

Before pilot start:

- backend and frontend critical tests pass
- seed data is validated
- required migrations are applied
- feature-flag settings are documented
- E2E manual flow is verified
- telemetry emission is confirmed

## Success Metrics

Suggested pilot metrics:

- session completion rate
- average attempts per puzzle
- hint usage distribution
- conflict recovery rate for gameplay v2
- telemetry completeness
- trace truncation rate
- user-reported confusion points

## Failure Triggers

Pause or revert if:

- session completion breaks
- attempts fail to update mastery correctly
- telemetry is missing or malformed
- conflict handling causes broken UI recovery
- gameplay v2 affects canonical attempt flow negatively

## Pilot Execution Notes

During pilot:

- keep gameplay v2 behind explicit approval
- document environment changes immediately
- do not mix undocumented content changes into active evaluation
- preserve clear participant grouping across conditions

## Post-pilot Review

After pilot:

1. summarize system stability
2. summarize telemetry quality
3. identify content or UX bottlenecks
4. review validity risks
5. decide whether to proceed, revise, or narrow scope

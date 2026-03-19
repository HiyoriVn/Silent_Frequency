# Puzzle Engine (Phase 3, Batch 2)

## Purpose

This document defines the lightweight interaction layer for Silent Frequency Phase 3.
The goal is to improve puzzle interaction quality without changing Phase 2 guarantees:

1. Backend owns progression.
2. Backend owns difficulty selection.
3. Backend owns scoring and completion.
4. Frontend remains display/input only.

This is not a game engine, room navigation system, or rules scripting system.

## Batch 2 Changes

Batch 2 introduces two additive backend changes:

1. Next-puzzle response extension:
   - `interaction_mode`: `plain` | `scene_hotspot`
   - `interaction`: optional interaction payload

2. Attempt trace support:
   - optional `interaction_trace` in attempt requests
   - telemetry-only logging in `event_log` as `puzzle_interaction_trace`

No new endpoints were added.
No DB migration was introduced.
No BKT or session-flow logic was modified.

## Interaction Data Flow

Content -> Seed validation -> Variant metadata -> Next-puzzle API -> Frontend render -> Attempt submit -> Event log telemetry

Detailed flow:

1. Puzzle content JSON may define an optional variant-level `interaction` block.
2. Seed validation enforces constraints and fail-fast errors.
3. Valid interaction is stored in `puzzle_variants.metadata.interaction`.
4. `GET /api/sessions/{session_id}/next-puzzle` reads from metadata only:
   - if present: `interaction_mode = "scene_hotspot"`, include payload
   - if absent: `interaction_mode = "plain"`, `interaction = null`
5. Frontend renders interaction payload when present.
6. Frontend submits answer as normal and may include optional `interaction_trace`.
7. Backend logs trace telemetry as a separate `event_log` row.

## API Contract Design

### GET /api/sessions/{session_id}/next-puzzle

Existing fields are unchanged.
Added optional/additive fields:

1. `interaction_mode`: `plain` | `scene_hotspot`
2. `interaction`: object or null

Backward compatibility:

- Plain puzzles continue to function with no content rewrite.
- Existing clients can ignore new fields.

### POST /api/sessions/{session_id}/attempts

Existing request fields and response fields are unchanged.
Added optional request field:

1. `interaction_trace`: array of interaction events (max 20)

Backward compatibility:

- Requests without `interaction_trace` remain valid.
- Existing attempt scoring behavior is unchanged.

## Telemetry Design

### Purpose of interaction_trace

`interaction_trace` captures user interaction observations (for analysis/debugging), not gameplay outcomes.

### Logging behavior

When trace is provided, backend writes:

- `event_type = "puzzle_interaction_trace"`
- payload includes:
  - `puzzle_id`
  - `variant_id`
  - `skill`
  - `trace`
  - `response_time_ms`

### Non-authoritative rule

Trace data is strictly telemetry and must never affect:

1. answer scoring
2. BKT updates
3. `current_level_index`
4. session completion
5. tier selection policy

## Interaction Schema Rules (Batch 2)

Current supported model is metadata-driven and constrained:

1. Trigger type: `click` only
2. Shape type: `rect` only
3. Multiple hotspots allowed
4. Exactly one hotspot must include `trigger.prompt_ref`
5. Every used `prompt_ref` must exist in `prompts`
6. No scripting, conditions, transitions, or state-machine fields

Validation split:

- API schemas: structure validation
- Seed validation: business constraints and fail-fast content rules

## Anti-Technical-Debt Decisions

1. No DB migration
   - JSONB metadata is already the extensibility path.

2. No frontend logic shift
   - Frontend only renders payload and submits trace.

3. No new endpoints
   - Existing endpoints were extended additively.

4. Metadata-driven design
   - Interaction source of truth is `metadata.interaction` only.

5. No hidden runtime engine
   - No script interpreter, no quest/state engine, no backend state machine.

## Extension Rules

Future schema extensions must follow these rules:

1. Keep all existing fields backward compatible.
2. Additive-only changes by default.
3. Introduce explicit versioning for interaction schema changes.
4. Keep business constraints centralized in seed validation.
5. Do not move scoring/progression logic to frontend.
6. Do not add endpoints unless existing endpoints are insufficient.

## Forbidden Future Changes

1. Frontend-owned correctness/progression.
2. Metadata scripting or executable rules.
3. Puzzle-specific hardcoded UI branches by puzzle ID.
4. DB schema expansion for convenience parsing only.
5. Trace-driven scoring or adaptive policy changes.

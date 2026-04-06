# Telemetry and Experiment Logging

## Purpose

Telemetry supports observation, debugging, and research analysis.

Telemetry must never become a source of truth for:

- scoring
- progression
- completion
- BKT updates

## Canonical Event Types

### `game_action`

Logs one resolved gameplay v2 action.

Minimum concepts:

- session identity
- action type
- target identity
- optional item identity
- timestamp
- minimal resulting effects

### `puzzle_interaction_trace`

Logs observational interaction traces.

Rules:

- bounded event count
- bounded payload size
- explicit truncation marker if trimming occurs

### `attempt_submitted`

Logs scoring pipeline events for answer submissions.

For gameplay v2 modal submissions, telemetry should include contextual metadata identifying gameplay v2 origin.

## Observational-only Rule

Telemetry data must not influence:

- correctness decisions
- BKT updates
- `current_level_index`
- session completion
- difficulty selection policy

## Retention and Privacy

Telemetry exports should:

- avoid exposing participant identity directly
- use anonymized participant codes where appropriate
- support participant data deletion requirements

## Metrics Expectations

The system should expose lightweight counters for:

- gameplay action count
- trace truncation
- oversized trace events

## Research Guidance

Telemetry is useful for:

- flow completion analysis
- interaction pattern observation
- hint usage analysis
- conflict recovery analysis
- comparing adaptive and static conditions

Telemetry alone is not sufficient to justify learning claims. Research conclusions must be tied to an explicit evaluation design and reported limitations.

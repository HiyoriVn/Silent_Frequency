# Session and Gameplay Flow

## Canonical Session Flow

The canonical learning flow is backend-owned and follows a fixed 9-step script.

### Progression Script

1. vocabulary, slot 1
2. vocabulary, slot 2
3. vocabulary, slot 3
4. grammar, slot 1
5. grammar, slot 2
6. grammar, slot 3
7. listening, slot 1
8. listening, slot 2
9. listening, slot 3

## Session Lifecycle

1. client creates a session
2. backend initializes player, session, mastery state, and game state
3. backend sets `current_level_index = 0`
4. client requests the next puzzle
5. backend resolves the current skill and slot
6. backend returns exactly one puzzle variant
7. client submits an attempt
8. backend scores the attempt and updates mastery
9. backend increments progression and evaluates completion

## Condition Policy

Supported conditions:

- `adaptive`
- `static`

### Static

All slots use the `mid` tier.

### Adaptive

- slot 1 always uses `mid`
- slots 2 and 3 may vary according to mastery state

## Frontend Responsibilities in Canonical Flow

The frontend should:

- start a session
- request the next puzzle
- render the returned puzzle
- submit the player answer
- render correctness, mastery, and completion feedback

The frontend must not:

- choose the next skill
- decide progression order
- determine when a session is complete

## Gameplay v2

Gameplay v2 is additive and experimental.

It introduces:

- room interaction
- object state
- inventory items
- typed action resolution
- gameplay telemetry

It must not silently replace canonical Phase-3 learning behavior.

## Gameplay v2 Rules

- session mode is selected at session creation
- mode is immutable during the session
- gameplay v2 is guarded by a feature flag
- gameplay v2 endpoints must reject non-v2 sessions

## Coexistence Rule

Gameplay v2 actions and canonical attempts coexist as follows:

- room or object actions may reveal or open a puzzle
- puzzle answers are still submitted through the attempt pipeline
- BKT and progression remain tied to attempts, not generic room actions

## Conflict Handling Rule

If gameplay v2 returns a stale-state or conflict response:

1. refetch canonical game state
2. replace stale local state
3. show a non-blocking refresh message
4. allow retry without hidden local mutation

# Frontend Flow and UI

## Frontend Role

The frontend is a rendering and interaction client for backend-owned game state.

Its responsibilities are:

- start sessions
- request next puzzles or gameplay snapshots
- render phases and room state
- collect player input
- submit attempts and actions
- recover gracefully from server conflicts

## Main Frontend State

The frontend store should mirror server-derived state such as:

- `session_id`
- `condition`
- `current_level_index`
- `session_complete`
- active puzzle or active room state
- inventory and dialogue state where applicable

## Canonical UI Flow

### Phase-3 Flow

1. show start form
2. create session
3. request next puzzle
4. render puzzle phase
5. submit attempt
6. display feedback
7. repeat until complete
8. show completion screen

### Gameplay v2 Flow

1. create gameplay v2 session
2. fetch canonical game state
3. render room scene and available interactions
4. submit one action at a time
5. apply declarative effects from backend response
6. open puzzle UI when instructed
7. submit attempts through the canonical attempt endpoint

## UI-local State vs Server-canonical State

### UI-local state is allowed for

- hover and focus state
- pressed and clicked animations
- panel open and close state
- local text input
- local dialogue animation progress

### Server-canonical state must remain backend-owned for

- object lock/unlock/reveal state
- inventory ownership and consumption
- puzzle solved state
- session progression
- mastery updates

## Accessibility Expectations

Interactive UI should support:

- keyboard focusability
- `Enter` and `Space` activation for interactive targets
- visible focus outlines
- modal focus trapping where needed
- `aria-live="polite"` for progressive dialogue text
- keyboard-accessible skip controls for dialogue animation

## Optimistic UI Policy

Do not optimistically mutate canonical gameplay state.

Allowed optimistic behavior is limited to:

- micro-animations
- hover or highlight feedback
- temporary loading indicators

Canonical state changes must be applied only after server response.

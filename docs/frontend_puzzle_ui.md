<!-- CHANGELOG: updated 2026-03-21: normalized to English and expanded gameplay v2 UI/accessibility/telemetry guidance -->

# Frontend Puzzle UI (Phase 3, Batch 3)

> **Phase-3 canonical:** The Batch 3 component and interaction model below remains canonical for the current production puzzle flow.

## 1. Component Architecture

Batch 3 introduces a minimal UI vertical slice with three components:

1. PuzzleScreen
   - Container-level puzzle rendering and local interaction state.
   - Reads current puzzle from store and submits answers via store action.

2. SceneRenderer
   - Pure renderer for interactive scene payload.
   - Draws clickable rect hotspots only.

3. AnswerPanel
   - Lightweight answer input form used by PuzzleScreen.
   - No game logic, only controlled input and submit action.

## 2. Data Flow

API -> PuzzleScreen -> SceneRenderer -> User Interaction -> Local Trace Buffer -> API

Detailed path:

1. `GET /next-puzzle` returns puzzle payload (plain or interactive).
2. PuzzleScreen decides render mode from `interaction_mode`.
3. SceneRenderer emits hotspot click events to PuzzleScreen.
4. PuzzleScreen appends trace events locally.
5. On submit, PuzzleScreen sends answer plus optional `interaction_trace`.
6. Backend remains authoritative for correctness, progression, and completion.

## 3. Interaction Model

Supported interaction behavior in Batch 3:

1. Hotspot click
   - User clicks a rect hotspot rendered by SceneRenderer.
   - PuzzleScreen records `hotspot_clicked` trace event.

2. Prompt reveal
   - If hotspot has `prompt_ref`, PuzzleScreen opens prompt text.
   - PuzzleScreen records `prompt_opened` trace event.

3. Answer submit
   - Plain mode: answer input is shown immediately.
   - Interactive mode: answer input is shown only after prompt hotspot is opened.
   - Submission includes optional trace events.

## 4. State Rules

### Local state (PuzzleScreen)

Interaction-specific state is local to PuzzleScreen:

1. active hotspot id
2. opened prompt ref
3. answer text
4. interaction trace buffer

### Global state (Zustand)

Zustand store remains a server-state mirror:

1. session IDs and status
2. current puzzle payload
3. mastery snapshot
4. last feedback

Why Zustand is not used for interaction state:

- interaction state is short-lived and puzzle-local
- keeping it local avoids hidden global game logic
- this preserves backend authority and reduces coupling

## 5. Anti-Technical-Debt Decisions

1. No puzzle engine
   - No scripting interpreter or state machine introduced.

2. No frontend gameplay authority
   - Frontend does not compute correctness or progression.

3. No API contract breakage
   - Only optional additive interaction fields are consumed.

4. No puzzle-id branching
   - Generic rendering via shared interaction schema.

5. No Zustand-driven interaction logic
   - Interaction remains local UI state only.

## 6. Extension Guidelines

To extend interaction safely:

1. Keep backend as source of truth for game decisions.
2. Extend schema additively and version interaction payloads.
3. Keep SceneRenderer generic (avoid puzzle-specific branches).
4. Keep interaction trace telemetry-only.
5. Validate new interaction features at seed/schema level before UI work.
6. Do not move progression, scoring, or mastery logic into frontend.

## Inventory & Knowledge Journal (experimental - gameplay v2)

> **experimental - gameplay v2:** Additive UI for room-based sessions only.

### Minimal Required Behaviors

- Inventory list shows canonical items in server order.
- Selecting an item reveals metadata (name, type, short description).
- Knowledge Journal groups clue/media entries and preserves acquisition order.
- No canonical mutation in UI: consume/remove/add changes only after backend `effects[]`.

### Keyboard Accessibility

- Modal inventory/journal must use a focus trap.
- Arrow keys move active option in the item list.
- `Enter` selects the active item.
- `Escape` closes modal and restores focus to opener.

### ARIA Semantics

- Item list container: `role="listbox"`.
- Item row: `role="option"` with `aria-selected`.
- Journal section headings use semantic heading levels.
- Modal root uses `role="dialog"` and `aria-modal="true"`.

## Dialogue & Typewriter Overlay (experimental - gameplay v2)

### Required Semantics

- New dialogue text must be announced with `aria-live="polite"`.
- Include a visible and keyboard-accessible skip control.
- Skip must fast-forward animation only; it must not drop queued dialogue messages.
- Queue behavior must be deterministic: FIFO based on backend order.

## UI-local vs Server-canonical State (experimental - gameplay v2)

### UI-local state (allowed)

- Hover/selection highlight.
- Press/click animation.
- Local panel open/close.
- Typewriter speed or animation progress.

### Server-canonical state (backend only)

- Object lock/unlock/reveal/consumed state.
- Inventory ownership and item consumption.
- Puzzle solved state.
- Session progression and mastery.

Example:

- Highlighting an object on click is allowed immediately.
- Changing a lock icon to unlocked is allowed only after an `unlock` effect is returned.

## Optimistic UI Policy (experimental - gameplay v2)

- Do not optimistically mutate canonical gameplay state.
- Allowed optimistic behavior is limited to micro-animations and temporary visual feedback.
- If an action fails, UI should clear temporary animation state and render the canonical server response.

## Telemetry Guidance (experimental - gameplay v2)

- Use `game_action` for action telemetry.
- Keep `puzzle_interaction_trace` for Phase-3 puzzle interaction trace telemetry.

Required `game_action` fields:

- `session_id`
- `action`
- `target_id`
- `item_id` (nullable)
- `client_action_id` (optional)
- `timestamp`
- `resulting_effects[]`

Example JS payload:

```js
const telemetryEvent = {
  event_type: "game_action",
  payload: {
    session_id: "4dc9c5f2-8fdb-45f2-9f31-0a6b4f87a111",
    action: "use_item",
    target_id: "old_radio",
    item_id: "bent_key",
    client_action_id: "6f627d0f-a72f-4a07-984f-dbe9f42c4b15",
    timestamp: new Date().toISOString(),
    resulting_effects: [
      { type: "unlock", target_id: "old_radio" },
      { type: "open_puzzle", puzzle_id: "listening_radio_01" }
    ]
  }
};
```


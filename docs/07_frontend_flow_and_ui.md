<!-- CHANGELOG: pass-2 canonical rewrite preserving Batch-3 UI model, gameplay_v2 accessibility, and telemetry guidance -->

# Frontend Flow and UI

## Scope

This document defines the frontend interaction model for Silent Frequency.

It covers:

- landing and player-entry flow
- pre-test and chapter-entry flow
- chapter-based room gameplay UI
- canonical Phase-3 puzzle UI
- gameplay v2 UI behavior
- local vs global state rules
- vocabulary board and journal behavior
- hint-system UI semantics
- accessibility expectations
- optimistic UI limits
- frontend telemetry guidance

---

## 1. Frontend Player Journey

The current thesis prototype frontend should support the following user-facing flow:

1. landing page
2. participant login or entry form
3. story introduction
4. short pre-test
5. chapter selection or chapter start
6. room-based gameplay
7. puzzle modal interaction
8. chapter completion
9. summary and optional post-test/questionnaire

### Rule

The frontend should present this as one coherent experience rather than as disconnected screens.

---

## 2. Chapter Gameplay Shell

The primary playable frontend path is a chapter-based room experience.

Recommended major UI containers include:

- `GameShell`
- `ZoneScene` or `RoomScene`
- `InventoryPanel`
- `KnowledgeJournal`
- `PagerHintPanel`
- `DialogueOverlay`
- `PuzzleModal`

Recommended shell-level context cues include:

- current zone title
- chapter title
- lightweight breadcrumb or location chip
- visible access to journal, inventory, and hint device

### Multi-zone Rule

A chapter may contain multiple connected zones within one map.

The frontend should support:

- clear current-zone context
- readable transitions between zones
- preservation of canonical state across zone changes
- minimal confusion about where clues and usable objects belong

---

## 3. Knowledge Journal and Vocabulary Board

The prototype should expose a knowledge-support surface that combines clue tracking and vocabulary support.

### Expected Behaviors

- display collected clue entries in canonical acquisition order
- show object names and related vocabulary
- show Vietnamese support meaning where authored
- optionally record solved puzzle summaries for later review
- allow optional quick access from the main gameplay shell or support menu
- preserve a distinction between always-available vocabulary support and newly unlocked clue/journal entries

### UX Rule

The journal should help the player remember and understand information already encountered.

It should not function as an unrestricted answer-reveal screen.

---

## 4. Bilingual UI Semantics

The frontend should preserve consistent language roles.

### Recommended Language Split

- world-facing objects, labels, signs, and puzzle prompts: primarily English
- support and guidance UI: primarily Vietnamese
- protagonist internal monologue: Vietnamese
- assistant hint system: Vietnamese
- glossary or vocabulary support: bilingual where useful

### Rule

Frontend components should not mix language roles inconsistently within the same interaction unless that is an intentional authored effect.

---

## 5. Pager-based Hint UI

The chapter prototype may include a diegetic hint system delivered through the assistant device.

### Suggested Model

- the player may open the pager or hint panel
- hint availability may depend on canonical backend state
- hint economy may be limited by authored resources such as battery units or chapter rules
- tutorial sections may expose guided hints early and less-guided hints later
- early tutorial states may provide more explicit guidance
- later states should reduce directness and encourage more player-led problem solving

### Frontend Rule

Hint UI may animate, pulse, or preview availability locally, but canonical hint availability and usage counts must remain backend-owned.
The frontend should visually communicate this shift in support style without changing canonical hint availability rules locally.

---

## 6. Canonical Puzzle Modal Architecture

Within chapter gameplay, learning puzzles should usually appear through a modal or overlay opened by canonical gameplay effects.

The minimal puzzle UI vertical slice is built from three core components:

### `PuzzleScreen`

Responsibilities:

- container-level puzzle rendering
- local puzzle interaction state
- submit answers via store or API client
- manage optional trace buffering

### `SceneRenderer`

Responsibilities:

- pure renderer for interaction payloads
- draw clickable rect hotspots only
- remain generic and puzzle-independent

### `AnswerPanel`

Responsibilities:

- lightweight answer input form
- controlled input only
- no game logic

---

## 7. Interactive Object Discoverability

A room-based prototype succeeds only if players can understand what is interactable.

### Required UX Signals

- interactable objects should be visually discoverable
- hover, focus, or tap states should be clear
- locked vs unlocked state should be understandable
- puzzle-trigger objects should feel distinct from decorative objects

### Recommended Techniques

- highlight on hover/focus
- cursor change
- outline or glow
- subtle motion or pulse where appropriate
- consistent iconography for locked, clue, and item-related objects

---

## 8. Zone Transition Behavior

When the chapter includes multiple connected zones, transitions should remain lightweight and readable.

### Rules

- preserve canonical state across zones
- do not reset local puzzle progress incorrectly when changing zones
- maintain clear breadcrumb or title context for current zone
- avoid unnecessary loading friction between connected spaces during the prototype

---

## 9. Inventory, Clue, and Resource Panels

### Minimal Required Behaviors

- inventory shows canonical items in server order
- clue and journal entries preserve acquisition order
- resource-like support items such as hint batteries may be displayed separately when authored
- selecting an item reveals metadata such as name, type, and short description
- canonical add/remove/consume changes must happen only after backend `effects[]`

### Rule

Frontend may visually separate:

- tools
- clues
- media
- support resources

but must not invent canonical ownership or quantities locally.

---

## 10. Pre-test UI Guidance

The pre-test should be presented as a short onboarding assessment rather than as a separate high-stakes exam.

### UX Guidance

- keep instructions concise
- keep progress visible
- avoid exhausting the player before chapter entry
- clearly communicate that the assessment helps tune the experience

### Rule

Pre-test results may affect initialization, but the frontend should not present them as a certified proficiency outcome.

---

## 11. Canonical Data Flow

For Phase-3 interactive puzzles, the data path is:

API -> PuzzleScreen -> SceneRenderer -> user interaction -> local trace buffer -> API

Detailed flow:

1. `GET /next-puzzle` returns puzzle payload
2. `PuzzleScreen` selects render mode from `interaction_mode`
3. `SceneRenderer` emits hotspot events to `PuzzleScreen`
4. `PuzzleScreen` appends trace events locally
5. on submit, `PuzzleScreen` sends answer plus optional `interaction_trace`
6. backend remains authoritative for correctness, progression, and completion

---

## 12. Canonical Interaction Model

Supported interaction behavior for the canonical additive puzzle interaction model:

### Hotspot Click

- user clicks a rect hotspot rendered by `SceneRenderer`
- `PuzzleScreen` records `hotspot_clicked`

### Prompt Reveal

- if a hotspot has `prompt_ref`, `PuzzleScreen` reveals the prompt text
- `PuzzleScreen` records `prompt_opened`

### Answer Submit

- plain mode: answer input is shown immediately
- interactive mode: answer input appears only after the prompt hotspot is opened
- submission may include `interaction_trace`

---

## 13. State Rules

### Local State in `PuzzleScreen`

Interaction-specific state should stay local:

1. active hotspot id
2. opened prompt ref
3. answer text
4. interaction trace buffer

### Global State in Zustand

Zustand should remain a server-state mirror for:

1. session ids and status
2. current puzzle payload
3. mastery snapshot
4. last feedback
5. canonical gameplay snapshot when gameplay v2 is enabled

### Why Interaction State Should Stay Local

- it is short-lived and puzzle-local
- it should not become hidden global game logic
- this reduces coupling
- this preserves backend authority

---

## 14. Anti-technical-debt UI Decisions

1. no hidden puzzle engine in frontend
2. no frontend gameplay authority
3. no contract-breaking client shape assumptions
4. no puzzle-id-specific hardcoded UI branching when a shared schema is sufficient
5. no Zustand-driven canonical interaction logic for puzzle-local state

---

## 15. Gameplay v2 UI Model

> **experimental — gameplay v2:** Additive room-based UI for sessions created in gameplay v2 mode.

Gameplay v2 may introduce components such as:

- `GameShell`
- `RoomScene`
- `InventoryPanel`
- `DialogueOverlay`
- `PuzzleModal`

### Gameplay v2 UI Flow

1. create gameplay v2 session
2. fetch canonical game state
3. render scene and interactive objects
4. submit action requests
5. update UI only after server response
6. open puzzle modal when an `open_puzzle` effect is returned
7. submit puzzle answer through canonical attempt endpoint

### Required Rule

The UI must not optimistically commit canonical room or inventory state.

Only server-confirmed state changes may become canonical in the frontend.

---

## 16. Asset and Identifier Conventions

Keep frontend keys aligned with backend content and telemetry joins.

Recommended conventions:

- `room_id`, `object_id`, `item_id`, `hotspot_id` use lowercase snake_case
- scene keys follow `scene_<room_id>`

Recommended asset paths:

- `public/scenes/<room_id>.png`
- `public/objects/<object_id>.png`

Do not rename shipped identifiers casually. Stable IDs matter for telemetry joins, debug replay, and trace interpretation.

---

## 17. Canonical Inventory Shape and Journal Data Rules

This section defines the canonical frontend-facing data expectations for inventory and journal rendering.

### Canonical Data Behaviors

This section defines canonical data-facing expectations for inventory and journal rendering, while Section 3 defines player-facing UX semantics.

- inventory list shows canonical items in server order
- selecting an item reveals metadata such as name, type, and short description
- knowledge journal groups clue and media entries
- acquisition order should be preserved
- canonical add/remove/consume changes must happen only after backend `effects[]`

### Canonical Inventory Item Shape

```json
{
  "id": "k1",
  "display_name": "Silver Key",
  "category": "tool",
  "consumed": false
}
```

---

## 18. Dialogue and Typewriter Overlay

### Required Semantics

- new dialogue text must be announced with `aria-live="polite"`
- include a visible and keyboard-accessible skip control
- skip should fast-forward animation only
- skip must not drop queued dialogue messages
- dialogue queue behavior must be deterministic and FIFO

---

## 19. Accessibility Requirements

### Keyboard Accessibility

- modal inventory and journal views must trap focus
- arrow keys should move active selection in list-style controls where applicable
- `Enter` selects the active item or action
- `Escape` closes modal dialogs and restores focus
- interactive scene objects should be keyboard focusable
- `Enter` and `Space` should activate scene objects
- focus outlines must remain visible

Example:

```html
<button role="button" aria-label="Safe" tabindex="0">...</button>
```

### Pointer and Touch Accessibility

- hotspots should provide a minimum tappable area close to 44x44 CSS pixels
- behavior should be equivalent across mouse, touch, and keyboard
- avoid hover-only affordances for required interactions

### ARIA Semantics

- item list container: `role="listbox"`
- item row: `role="option"` with `aria-selected`
- modal root: `role="dialog"` and `aria-modal="true"`
- journal sections should use semantic heading levels

---

## 20. UI-local vs Server-canonical State

### Allowed UI-local State

- hover highlight
- selection highlight
- press animation
- panel open and close
- typewriter speed or animation progress

### Backend-only Canonical State

- object lock/unlock/reveal/consumed state
- inventory ownership and item consumption
- puzzle solved state
- session progression
- mastery

Example:

- highlighting an object on click is allowed immediately
- changing a lock icon to unlocked is allowed only after an `unlock` effect returns from the server

---

## 21. Optimistic UI Policy

Do not optimistically mutate canonical gameplay state.

Allowed optimistic behavior is limited to:

- micro-animations
- local loading indicators
- temporary interaction feedback

If an action fails:

- clear temporary animation state
- render canonical server response
- avoid preserving stale local assumptions

---

## 22. Conflict Handling

If gameplay v2 returns `409`:

1. refetch canonical game state
2. replace stale local state
3. show a non-blocking refresh message
4. allow retry without hidden local mutation

This is required for safe stale-state recovery.

---

## 23. Frontend Telemetry Guidance

### Use `game_action` for

- gameplay v2 room/object action telemetry

### Use `puzzle_interaction_trace` for

- Phase-3 or modal puzzle interaction trace telemetry

Required `game_action` fields:

- `session_id`
- `action`
- `target_id`
- `item_id` when applicable
- `client_action_id` when available
- `timestamp`
- `resulting_effects[]`

Example payload:

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
      { type: "open_puzzle", puzzle_id: "listening_radio_01" },
    ],
  },
};
```

### Rule

Telemetry is for observation only. It must not affect correctness, mastery, or progression.

---

## 24. Frontend Test Expectations

Frontend changes should be validated through:

- component tests
- interaction tests
- API mocking for deterministic behavior
- stale-state conflict handling tests
- accessibility-sensitive interaction checks where relevant

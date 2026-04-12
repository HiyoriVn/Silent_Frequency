# Phase 2 — Room 404 Game State and Vertical Slice

## 1. Goal

Implement the first playable gameplay_v2 vertical slice for Chapter 1 using Patient Room 404 only.

At the end of this phase, a tester should be able to:

- start from the existing Phase 1 session flow
- enter a canonical Room 404 gameplay state
- see a placeholder background
- click visible hotspots
- open a sub-view
- collect at least one clue or item
- trigger at least one puzzle modal
- solve at least one puzzle and unlock a simple progression flag

This phase is the first step from onboarding into actual playable game structure.

---

## 2. In Scope

- minimal canonical game state model for chapter gameplay
- Patient Room 404 only
- placeholder `bg_view` and `sub_view` support
- hotspot visibility and clickability rules
- `GET /api/sessions/{session_id}/game-state` or equivalent canonical state fetch
- `POST /api/sessions/{session_id}/action` or equivalent action endpoint
- minimal frontend RoomScene / GameShell rendering for Room 404
- one sub-view open/close flow
- one clue/item collection flow
- one simple puzzle trigger flow
- one simple progression flag update after puzzle success

---

## 3. Out of Scope

- Nurse Station
- Hallway
- Security Office
- Ambulance Bay
- full chapter traversal
- full asset integration
- polished visuals
- complete journal system
- complete inventory UX
- full BKT adaptation logic
- full puzzle bank integration
- final chapter completion flow
- broad refactors outside gameplay state slice

---

## 4. Required Inputs

Phase 2 should follow these project decisions:

- use the chapter-based prototype direction
- preserve backend ownership of canonical gameplay state
- use Patient Room 404 as the only gameplay zone in this phase
- use placeholder assets if final design assets are not ready
- keep `bg_view` / `sub_view` taxonomy consistent with the spatial docs
- use current session output from Phase 1 as the entry point

Use the agreed structures from:

- spatial and zone spec
- objects/items/FSM spec
- hotspot prerequisite matrix
- puzzle list and mapping
- prerequisites and tier mapping

For this phase, only implement the minimum subset needed for Room 404.

---

## 5. Minimum Vertical Slice Scope for Room 404

The vertical slice should include only:

### Views

- `patient_room_404__bg_01_bed_wall`
- `patient_room_404__bg_04_door_side`
- `patient_room_404__sub_bedside_drawer`

### Hotspots

At minimum:

- `bedside_table`
- `folded_note`
- `warning_sign`
- `main_door`

### Puzzle

At minimum:

- `p_warning_sign_translate`

### Flags

At minimum:

- `first_language_interaction_done`
- `bedside_note_collected`
- `room404_exit_unlocked`

### Expected playable loop

1. user enters session from Phase 1
2. Room 404 initial state loads
3. user clicks `bedside_table`
4. sub-view opens
5. user collects `folded_note`
6. user returns to main view
7. user clicks `warning_sign`
8. puzzle opens
9. user submits correct answer
10. backend sets progression flag
11. `main_door` becomes unlocked or changes feedback state

---

## 6. Batches

## Batch 2.1 — Canonical gameplay state model

### Goal

Introduce the minimum canonical game/session state needed for Room 404 gameplay.

### Tasks

- define or extend a minimal gameplay state structure
- include:
  - `chapter_id`
  - `zone_id`
  - `view_id`
  - `sub_view_id`
  - `fsm_state`
  - `flags`
  - `inventory`
  - `journal_entries`
  - `game_state_version`
- ensure state belongs to backend/session context, not guessed by frontend
- initialize Room 404 default state when a session enters gameplay

### Allowed files

- backend session/game state models
- backend session service/state init files
- backend schemas/types related to game state
- frontend API/types only if needed to consume the new shape

### Do not touch

- Nurse Station and later zones
- puzzle scoring internals beyond minimal wiring
- BKT internals
- unrelated auth code

### Done criteria

- a newly started session can produce an initial Room 404 gameplay state
- state shape is stable enough for frontend consumption
- no frontend-only canonical gameplay state is introduced

### Manual test

1. create a fresh session from Phase 1 flow
2. inspect backend response or debug output
3. confirm initial game state includes Room 404 identifiers and empty/default flags

---

## Batch 2.2 — Room 404 data binding

### Goal

Provide the minimum Room 404 content/state data needed for rendering and actions.

### Tasks

- add minimal data source for Room 404:
  - one zone
  - two bg views
  - one sub-view
  - visible hotspots
- bind hotspot metadata for:
  - visibility
  - clickability
  - type
  - target action
- use placeholder assets or placeholder view references if final assets are not ready

### Allowed files

- gameplay content/data files
- JSON/mock/static config files for Room 404
- backend state/content loader files
- frontend types only if required

### Do not touch

- full chapter data
- other zones
- final asset pipeline
- unrelated docs

### Done criteria

- backend or shared data layer can resolve the Room 404 vertical slice
- each required hotspot has a stable ID and action type
- placeholder asset references are accepted

### Manual test

1. inspect Room 404 data source
2. confirm required views and hotspots exist
3. confirm hotspot IDs match the agreed spec

---

## Batch 2.3 — Canonical game-state fetch

### Goal

Expose the Room 404 gameplay snapshot to the frontend.

### Tasks

- implement or extend canonical game-state fetch endpoint
- return:
  - current zone/view/sub-view
  - visible hotspots
  - clickable state
  - inventory
  - journal entries
  - flags
  - game_state_version
- ensure response is deterministic and backend-owned

### Allowed files

- backend routes/schemas/services for game-state fetch
- frontend API client/types
- minimal frontend wiring to load the snapshot

### Do not touch

- action resolver beyond what is needed for read path
- puzzle modal logic
- later zones
- unrelated session/auth logic

### Done criteria

- frontend can fetch a valid Room 404 snapshot
- snapshot includes hotspot visibility/clickability state
- response is sufficient for rendering placeholder room UI

### Manual test

1. create a session
2. call game-state fetch
3. confirm Room 404 snapshot is returned
4. confirm required hotspots are present

---

## Batch 2.4 — Action resolver for the Room 404 slice

### Goal

Support a minimal set of gameplay actions for the Room 404 vertical slice.

### Tasks

Implement only the minimum action types required:

- `inspect`
- `open_sub_view`
- `collect`
- `navigation` or locked-navigation feedback

Minimum supported interactions:

- open `patient_room_404__sub_bedside_drawer`
- collect `folded_note`
- return to main view
- inspect or interact with `main_door`
- return locked/unlocked feedback
- prepare support for `warning_sign` puzzle trigger

### Allowed files

- backend action route/service
- game-state mutation logic
- frontend API client/types for actions
- minimal frontend action wiring

### Do not touch

- later chapter zones
- full inventory/journal UX polish
- BKT internals
- broad gameplay architecture refactor

### Done criteria

- clicking `bedside_table` opens the sub-view
- clicking `folded_note` collects the clue/item
- game state updates reflect the collection
- clicking `main_door` returns correct locked/unlocked feedback state

### Manual test

1. load Room 404
2. click bedside table
3. confirm sub-view opens
4. click folded note
5. confirm it is collected
6. return to main view
7. click main door
8. confirm locked feedback is returned before puzzle success

---

## Batch 2.5 — Frontend RoomScene placeholder

### Goal

Render the Room 404 gameplay slice in the frontend with placeholder visuals and working hotspots.

### Tasks

- implement or extend a minimal RoomScene/GameShell UI
- render current background placeholder
- render hotspots from canonical state
- support hotspot click interactions
- open/close sub-view
- show simple feedback or placeholder UI for inventory/journal data
- wire one puzzle trigger path for the next phase boundary

### Allowed files

- frontend gameplay shell/scene files
- frontend API helpers/types
- placeholder asset references
- minimal local UI state for rendering only

### Do not touch

- polished scene rendering
- final asset integration
- broad app navigation refactor
- later chapter zones

### Done criteria

- a tester can visually enter Room 404
- hotspots are clickable
- sub-view opens and closes
- collected clue/item visibly changes state somehow
- the room is testable without final assets

### Manual test

1. finish Phase 1 flow and enter gameplay
2. confirm Room 404 placeholder screen renders
3. click hotspots
4. open bedside drawer sub-view
5. collect folded note
6. confirm UI/state updates
7. confirm no crash

---

## 7. API Expectations

By the end of Phase 2, the system should support at least:

### Session entry

- use the existing session result from Phase 1

### Game-state read

- canonical Room 404 snapshot fetch

### Action write

- minimal gameplay action endpoint for Room 404 slice

### Puzzle trigger readiness

- enough state/action support so the warning sign puzzle can be opened in the next phase or late in this phase if already convenient

---

## 8. Expected Deliverables

At the end of Phase 2, the repo should contain:

- initial canonical gameplay state model
- Room 404 minimal data binding
- Room 404 game-state fetch path
- minimal action resolver for Room 404 slice
- frontend placeholder room rendering
- one working sub-view interaction
- one working collect interaction
- one locked progression path ready to be unlocked by puzzle success

---

## 9. Done Criteria for Phase 2

Phase 2 is complete only if:

- the user can enter a Room 404 gameplay state from Phase 1
- Room 404 placeholder background is rendered
- hotspots are visible and clickable
- one sub-view opens correctly
- one clue/item can be collected
- backend canonical state updates correctly
- frontend reflects the updated state
- no broad unrelated refactor is introduced

---

## 10. Risks to Avoid

- implementing too much of the chapter at once
- hardcoding gameplay state only on the frontend
- skipping canonical hotspot visibility/clickability rules
- waiting for final assets before testing interactions
- mixing puzzle scoring and room action logic too early
- expanding beyond Room 404 before the vertical slice is stable

---

## 11. Manual Test Guide

### Test 1 — Enter gameplay state

1. complete Phase 1 flow
2. start a session
3. confirm app reaches Room 404 placeholder gameplay state

### Test 2 — Room render

1. confirm Room 404 placeholder background appears
2. confirm required hotspots are visible

### Test 3 — Open sub-view

1. click `bedside_table`
2. confirm `patient_room_404__sub_bedside_drawer` opens
3. confirm return/back behavior works

### Test 4 — Collect clue/item

1. click `folded_note`
2. confirm it is collected
3. confirm game state or UI reflects the change

### Test 5 — Locked progression feedback

1. click `main_door` before puzzle success
2. confirm locked/blocked feedback is shown
3. confirm no crash occurs

---

## 12. Completion Log Template

When Codex completes this phase, add a completion block to `docs/output/phase_2.md`:

### Implementation completion log

- date:
- owner:
- Codex version/mode used:
- files changed:
- endpoints added/updated:
- schemas changed:
- tests run:
- manual test result:
- blockers remaining:
- notes for Phase 3:

---

## 13. Suggested Prompt Strategy for Codex

Do not ask Codex to implement all of Phase 2 at once.

Run it batch by batch:

- Batch 2.1
- Batch 2.2
- Batch 2.3
- Batch 2.4
- Batch 2.5

Each prompt should:

- ask Codex to read this phase doc first
- scope to one batch only
- list allowed files
- list do-not-touch areas
- require a file-change summary
- require manual test steps
- require output log update

---

## 14. Condition to Move to Phase 3

Only move to Phase 3 when:

- Room 404 vertical slice is stable
- canonical state fetch and update both work
- at least one sub-view and one collect interaction are working
- frontend can render the room without relying on final assets
- there are no blocker regressions from Phase 1

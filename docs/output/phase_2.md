# Phase 2 — Output Log and Verification Notes

## Batches Implemented

- Batch 2.1 — Canonical gameplay state model
- Batch 2.2 — Room 404 data binding
- Batch 2.3 — Canonical game-state fetch
- Batch 2.4 — Action resolver for the Room 404 slice
- Batch 2.5 — Frontend RoomScene placeholder

---

## Phase 2 Summary

Phase 2 established the first playable vertical slice for Chapter 1 using **Patient Room 404** only.

At the end of this phase:

- backend owns the canonical gameplay state
- Room 404 has a minimal content/config contract
- `GET /api/sessions/{session_id}/game-state` returns a reduced canonical read-model
- `POST /api/sessions/{session_id}/action` supports the minimum Room 404 mutation path
- frontend renders a Room 404 placeholder UI using canonical `hotspots[]`
- the Room 404 loop is playable end-to-end with placeholder visuals

This phase is considered the first working gameplay slice built on top of the Phase 1 onboarding/session flow.

---

## Batch 2.1 — Canonical Gameplay State Model

### Summary

Implemented a minimal backend-owned canonical gameplay state for the Room 404 vertical slice.

### Canonical gameplay state fields

- `chapter_id`
- `zone_id`
- `view_id`
- `sub_view_id`
- `fsm_state`
- `flags`
- `inventory`
- `journal_entries`
- `game_state_version`

### Initialization behavior

For a new `gameplay_v2` session, backend initialization now seeds:

- `chapter_id`
- `zone_id = patient_room_404`
- `view_id = patient_room_404__bg_01_bed_wall`
- `sub_view_id = null`
- initial `fsm_state`
- baseline flags
- empty inventory
- empty journal entries

### Files changed

- `backend/app/services/session_service.py`
- `backend/app/services/game_service.py`
- `backend/app/api/schemas.py`
- `frontend/src/lib/types.ts`

### Tests run

- `pytest backend/app/tests/test_gameplay_v2_models.py -q`
- `pytest backend/app/tests/test_gameplay_v2_schemas.py -q`
- `pytest backend/app/tests/test_gameplay_v2_flow.py -q`
- `cd frontend && npm run lint`

### Result

Pass.

---

## Batch 2.2 — Room 404 Data Binding

### Summary

Added the minimum Room 404 content/config contract required for the vertical slice.

### Room 404 content added

Room template file:

- `backend/app/content/rooms/patient_room_404.json`

Views included:

- `patient_room_404__bg_01_bed_wall`
- `patient_room_404__bg_04_door_side`
- `patient_room_404__sub_bedside_drawer`

Required hotspots included:

- `bedside_table`
- `folded_note`
- `warning_sign`
- `main_door`

### Hotspot metadata contract

Each required hotspot includes:

- `id`
- `parent_view_id`
- `type`
- `visibility_intent`
- `clickability_intent`
- `target_action` and/or `target_view_id`

### Session entry alignment

`gameplay_v2` session entry now resolves Room 404 as the active starting room.

### Files changed

- `backend/app/content/rooms/patient_room_404.json`
- `backend/app/services/session_service.py`

### Tests run

- `pytest backend/app/tests/test_seed_rooms_validation.py -q`
- `pytest backend/app/tests/test_gameplay_v2_flow.py -q`
- `pytest backend/app/tests/test_gameplay_v2_models.py -q`

### Result

Pass.

---

## Batch 2.3 — Canonical Game-State Fetch

### Summary

Implemented a reduced backend-owned canonical read-model for:

- `GET /api/sessions/{session_id}/game-state`

### Read-model additions

The read model now includes:

- all canonical state fields from Batch 2.1
- `current_background_view_id`
- `hotspots[]`

### Canonical hotspot read-model

Each hotspot entry includes:

- `id`
- `type`
- `parent_view_id`
- `visible`
- `clickable`
- `target_view_id`
- `action_hint`

### Important architecture note

Frontend does **not** need to understand raw room template internals.  
The backend read layer reduces the template/config into a frontend-friendly payload.

### Files changed

- `backend/app/services/game_service.py`
- `backend/app/api/schemas.py`
- `frontend/src/lib/types.ts`

### Tests run

- `pytest backend/app/tests/test_gameplay_v2_flow.py -q`
- `pytest backend/app/tests/test_gameplay_v2_schemas.py -q`
- `pytest backend/app/tests/test_gameplay_v2_models.py -q`
- `cd frontend && npm run lint`

### Result

Pass.

---

## Batch 2.4 — Action Resolver for the Room 404 Slice

### Summary

Implemented the minimum canonical mutation path for Room 404 actions.

### Supported canonical actions

- `inspect`
- `open_sub_view`
- `collect`
- `navigation`

### Minimum supported interactions

- `bedside_table` opens `patient_room_404__sub_bedside_drawer`
- `folded_note` is collectible exactly once
- returning from sub-view to main view works
- `main_door` returns locked/unlocked feedback based on canonical state flags
- `warning_sign` can trigger puzzle-open effect without full puzzle scoring

### Files changed

- `backend/app/services/game_service.py`
- `backend/app/api/schemas.py`
- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`

### Tests run

- `pytest backend/app/tests/test_gameplay_v2_flow.py -q`
- `pytest backend/app/tests/test_gameplay_v2_schemas.py -q`
- `pytest backend/app/tests/test_gameplay_v2_models.py -q`
- canonical Room 404 action smoke script
- `cd frontend && npm run lint`

### Result

Pass.

---

## Batch 2.4 Technical Debt Cleanup

### Summary

A small post-implementation cleanup pass was completed to isolate and document the temporary compatibility bridge.

### Purpose

The cleanup was done to avoid carrying scattered legacy-mapping logic into frontend placeholder rendering.

### Cleanup result

The temporary Room 404 compatibility bridge is now explicitly centralized in:

- `backend/app/services/game_service.py`

### Current temporary mappings

- `bedside_table -> drawer`
- `folded_note -> note`
- `warning_sign -> old_radio`

### Rule

This compatibility bridge must remain **backend-internal only**.

Frontend Room 404 flow must use:

- canonical hotspot IDs
- canonical action values

### Result

Pass, with no intended behavior change.

---

## Batch 2.5 — Frontend RoomScene Placeholder

### Summary

Implemented a minimal Room 404 placeholder UI path that consumes canonical `game_state.hotspots[]` directly for rendering and action dispatch.

### Frontend behavior now works like this

- frontend derives active view from canonical fields:
  - `sub_view_id`
  - `current_background_view_id`
  - `view_id`
- visible hotspots are rendered from canonical `hotspots[]`
- hotspot clicks dispatch canonical actions
- a minimal Room 404 loop is playable in the browser
- placeholder visuals are used instead of final assets

### Canonical Room 404 interactions in frontend

- `bedside_table` → `open_sub_view`
- `folded_note` → `collect`
- `main_door` → `navigation`
- `warning_sign` with `action_hint = open_puzzle` is translated to canonical `inspect` request to trigger backend puzzle-open effect

### Frontend files changed

- `frontend/src/components/PuzzleScreen.tsx`
- `frontend/src/components/SceneRenderer.tsx`

### Tests run

- `npm run tsc`
- `npm run lint`
- `npm run test`

### Result

Pass.

---

## Developer Verification — Phase 2 Room 404 Vertical Slice

This section is for developer/API-level verification.

### Verify canonical snapshot

1. Start a fresh `gameplay_v2` session.
2. Call `GET /api/sessions/{session_id}/game-state`.
3. Confirm `data.game_state` includes:
   - `chapter_id`
   - `zone_id`
   - `view_id`
   - `sub_view_id`
   - `fsm_state`
   - `flags`
   - `inventory`
   - `journal_entries`
   - `game_state_version`
   - `current_background_view_id`
   - `hotspots[]`

### Verify canonical hotspot payload

Confirm each hotspot entry includes:

- `id`
- `type`
- `parent_view_id`
- `visible`
- `clickable`

### Verify minimum Room 404 action loop

1. POST action `open_sub_view` with target `bedside_table`
2. Confirm `sub_view_id = patient_room_404__sub_bedside_drawer`
3. POST action `collect` with target `folded_note`
4. Confirm:
   - `folded_note` appears in inventory
   - `flags.bedside_note_collected = true`
5. Repeat collect once
6. Confirm item is not duplicated
7. POST action `navigation` back to `patient_room_404__bg_01_bed_wall`
8. Confirm `sub_view_id = null`
9. POST action `navigation` with target `main_door`
10. Confirm locked/unlocked feedback is returned from backend effects

---

## Manual Tester Flow — Phase 2 Room 404 Vertical Slice

This section is for browser/manual testing only.

### Goal

Verify that the Room 404 vertical slice is playable from the current frontend flow.

### Steps

1. Complete the existing Phase 1 onboarding flow.
2. Start a `gameplay_v2` session.
3. Confirm the Room 404 placeholder screen appears.
4. Confirm visible hotspots appear in the room UI.
5. Click **Bedside Table**.
6. Confirm the bedside drawer sub-view opens.
7. Click **Folded Note**.
8. Confirm the note is collected and the UI reflects the collected state.
9. Click **Back To Main View**.
10. Switch to **Door Side View** if available.
11. Click **Main Door**.
12. Confirm locked feedback appears when the room is not yet unlocked.
13. Confirm the app does not crash at any point.

### Expected result

- Room 404 renders successfully
- visible hotspots are clickable
- sub-view opens and closes correctly
- collected state changes are visible
- locked navigation feedback works
- no crash occurs during the loop

---

## Known Technical Notes

### Temporary compatibility bridge

A temporary backend-only compatibility bridge still exists for some Room 404 legacy target IDs.

It is centralized in:

- `backend/app/services/game_service.py`

This bridge exists to preserve older gameplay_v2 compatibility while the new canonical Room 404 path is being stabilized.

### Important contract rule

Frontend code for the Room 404 placeholder UI must use:

- canonical hotspot IDs
- canonical action values

Frontend must **not** implement legacy mapping.

---

## Blockers Before Phase 3

- replace temporary placeholder hotspot layout coordinates with content-driven coordinates in canonical room metadata
- formalize door interaction semantics (`clickable` vs locked feedback expectations) so UI behavior and backend clickability intent are fully aligned
- decide when to remove the frontend compatibility fallback path once all tests/fixtures are canonical-hotspot based

---

## Phase 2 Closure Note

Phase 2 is considered complete.

Implemented batch coverage:

- Batch 2.1 — Canonical gameplay state model
- Batch 2.2 — Room 404 data binding
- Batch 2.3 — Canonical game-state fetch
- Batch 2.4 — Action resolver for the Room 404 slice
- Batch 2.5 — Frontend RoomScene placeholder

Phase 2 outcome:

- Room 404 vertical slice is playable with placeholder UI
- frontend consumes canonical `hotspots[]` for the new Room 404 path
- backend remains the source of truth for canonical gameplay state and action mutation

Carry-forward notes for Phase 3:

- build puzzle modal flow on top of the current Room 404 slice
- avoid reintroducing legacy `room_state` hotspot extraction for the new Room 404 path
- continue retiring temporary compatibility bridges only when safe

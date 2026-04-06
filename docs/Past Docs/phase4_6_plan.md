# PHASE 4–6 Plan (Revised for gameplay_v2)

**Note:** Phase-3 (linear `next-puzzle` + `attempts`) remains canonical. The steps below describe an additive extension for **gameplay_v2** (room-based interactions, inventory, action/effects). All gameplay_v2 features must be versioned (`interaction_schema_version = 2`) and enabled per session via a mode flag.

---

## PHASE 4 — Frontend Refactor & Interactive UX (revised)

**Goal:** Deliver a stable, testable interactive frontend that supports both Phase-3 and gameplay_v2: UI shell, scene renderer, inventory, action flow, hint system, accessibility, telemetry. The backend remains authoritative for canonical state and scoring.

### Batch 4.0 — Architecture spike & feature flag

- **Goal:** Implement backend stubs for `GET /api/sessions/{session_id}/game-state` and `POST /api/sessions/{session_id}/action`; add a sample room/item in seed; add `mode` to `POST /api/sessions` to enable gameplay_v2 per session.
- **Deliverable:** Working stubs, sample room JSON, session created with `mode: gameplay_v2`.
- **Verification:** `GET /game-state` returns a canonical snapshot; `POST /action` returns `effects[]`.

### Batch 4.1 — Core models & validation

- **Goal:** Implement backend data models (Pydantic) for `Room`, `Object`, `Item`, `GameStateSnapshot`, `ActionRequest`, `ActionResponse`, `EffectUnion`, `ErrorResponse`. Extend `seed.py` to validate room and item JSON.
- **Deliverable:** Pydantic models, seed validation, unit tests.
- **Verification:** Validator accepts sample room files; model unit tests pass.

### Batch 4.2 — Frontend shell & components

- **Goal:** Build `GameShell`, `RoomScene` (SceneRenderer v2), `InventoryPanel`, `DialogueOverlay`, and `PuzzleModal` (re-usable for learning puzzles). Implement keyboard accessibility and ARIA patterns.
- **Deliverable:** Frontend components and component tests.
- **Verification:** Components render game-state snapshots; keyboard navigation and basic accessibility checks pass.

### Batch 4.3 — Action flow & telemetry

- **Goal:** Implement client action flow: send `ActionRequest` (optionally with `client_action_id`), handle `effects[]`, update UI only after server response. Implement `game_state_version`/ETag handling and client behavior for 409/conflict responses. Implement `game_action` telemetry and extend `puzzle_interaction_trace` with `hint_opened`.
- **Deliverable:** Action handling code, telemetry generation, integration tests.
- **Verification:** Integration test where `POST /action` yields `add_item` and `open_puzzle` effects and the client updates UI after response; telemetry events recorded with correct fields.

### Batch 4.4 — Learning puzzle integration & hint system

- **Goal:** Wire `open_puzzle` effect to the existing learning attempt flow (`POST /api/sessions/{session_id}/attempts`). Implement HintPanel with unique-hint counting (unique reveals per attempt) and server-configurable auto-hint policy (e.g., `idle_seconds`, `failed_attempts_threshold`).
- **Deliverable:** Puzzle modal wiring, hint UI and hint counting, server hint policy hooking.
- **Verification:** `POST /attempts` flow functions inside the puzzle modal; `hint_count_used` and `interaction_trace` are included in attempt payloads as expected.

### Batch 4.5 — Integration & QA

- **Goal:** Full integration tests, telemetry QA, content QA for sample rooms, and pilot readiness.
- **Deliverable:** QA checklist, pilot plan, and test suite.
- **Verification:** All tests pass; pilot checklist complete.

---

## PHASE 5 — Adaptive Engine Integration (revised)

**Goal:** Ensure BKT integration and calibration remain correct when learning puzzles are triggered from gameplay_v2. Keep `POST /attempts` behavior unchanged and ensure analytics map gameplay actions to learning outcomes.

### Batch 5.1 — BKT audit & parameter review

- **Goal:** Review `bkt_core.py`, add unit tests for update semantics (varied guess/slip/transition scenarios).
- **Verification:** Unit tests pass.

### Batch 5.2 — Calibration pilot & data collection

- **Goal:** Collect pilot data in a training mode for calibration; add export scripts for required fields (CSV/Parquet).
- **Verification:** Export file contains required fields; pilot data collected for analysis.

### Batch 5.3 — Analytics & reporting

- **Goal:** Provide notebooks/scripts to compute pre/post gains, mastery growth, correlations (e.g., final mastery vs. post-test), and group comparisons. Document analysis plan in `docs/experiment_pipeline.md`.
- **Verification:** Example plots and initial report draft available.

**Note:** Always analyze Phase-3 and gameplay_v2 cohorts separately.

---

## PHASE 6 — Telemetry System & Data Pipeline (revised)

**Goal:** Formalize telemetry, implement export pipeline, and provide a lightweight dashboard to monitor data quality and key metrics.

### Batch 6.1 — Telemetry schema & event catalog

- **Goal:** Define canonical event types and payload shapes including `game_action`, `puzzle_interaction_trace`, `attempt_submitted`, `session_created`, `session_finished`. Add event versioning, size limits, and retention policy.
- **Verification:** Event catalog doc and tests validating payload shapes.

### Batch 6.2 — Export & pipeline scripts

- **Goal:** Implement scripts to export SQL → CSV/Parquet and a reproducible notebook for standard analyses. Implement anonymization for participant data.
- **Verification:** Sample export runs and notebook completes.

### Batch 6.3 — Lightweight dashboard & QA

- **Goal:** Build a static report or lightweight dashboard showing participant counts, completion rate, average gain, hint usage, response times, and mastery distribution. Add QA scripts to detect missing or malformed events.
- **Verification:** Dashboard renders sample data; QA scripts execute successfully.

---

## Cross-phase guardrails (always)

- **Backend authority:** Canonical state (objects, inventory, puzzle solved, progression, BKT) must live in backend. Frontend must never compute mastery or progression.
- **Versioning:** All v2 artifacts must include `interaction_schema_version = 2`. Phase-3 artifacts remain `interaction_schema_version = 1`.
- **Telemetry is observational-only:** Telemetry must not influence scoring, BKT updates, or progression.
- **No client scoring:** The frontend must never determine correctness or modify mastery.
- **Seed validation:** New room/item content must pass seed validation before enabling gameplay_v2.
- **Atomic effects:** Backend must apply `effects[]` atomically and return updated canonical `room_state` and `inventory`.
- **Per-session feature flag:** Enable gameplay_v2 per session via a `mode` flag at session creation.

---

## Owners / Responsibilities

- **Frontend lead:** GameShell, RoomScene, Inventory UI, accessibility, component tests.
- **Backend lead:** Action endpoints (`/game-state`, `/action`), Pydantic models, seed validator, auto-hint policy.
- **Adaptive lead:** BKT audit and calibration scripts.
- **Data manager:** Telemetry catalog, export scripts, dashboard and data QA.
- **Content lead:** Create and QA sample rooms, objects, items, and puzzles.

---

## Per-phase verification checklist (run for each batch)

1. Unit tests for new models and handlers pass.
2. Integration tests verify action → server `effects[]` → canonical state update.
3. Telemetry events (`game_action`, `puzzle_interaction_trace`) are emitted and match schema.
4. Seed validation accepts sample content and rejects invalid references.
5. Accessibility checks: keyboard navigation, ARIA attributes, `aria-live` for dialogues.
6. Manual end-to-end check or small pilot validates UX and data collection.

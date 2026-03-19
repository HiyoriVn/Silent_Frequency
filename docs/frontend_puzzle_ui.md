# Frontend Puzzle UI (Phase 3, Batch 3)

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

1. session ids and status
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

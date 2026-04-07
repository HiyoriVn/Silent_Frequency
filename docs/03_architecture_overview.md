<!-- CHANGELOG: pass-2 canonical rewrite preserving repository audit findings, layering, and gameplay_v2 implications -->

# Architecture Overview

## Scope

This document describes the accepted baseline architecture of Silent Frequency.

It covers:

- backend and frontend layering
- canonical ownership boundaries
- stable modules to preserve
- common misalignment risks
- additive gameplay v2 architecture
- architectural change rules for maintainers

> **Phase-3 canonical:** The accepted production baseline remains backend-owned progression through canonical session endpoints. Gameplay v2 is additive and must remain explicitly gated.

---

## 1. Architectural Principles

Silent Frequency is designed around a small number of strong architectural rules:

1. backend owns progression
2. backend owns scoring
3. backend owns completion state
4. backend owns mastery updates
5. frontend is a rendering and input client
6. telemetry is observational only
7. additive interaction features must not silently alter canonical learning flow

These principles protect both maintainability and experimental validity.

---

## 2. High-level Runtime Architecture

Current architecture is a standard split:

- FastAPI backend with service layer and SQLAlchemy ORM
- Next.js frontend with Zustand client state
- BKT and content selection engines in backend
- relational persistence for puzzles, attempts, sessions, and events
- file-driven puzzle and room content

### High-level Runtime Flow

1. frontend creates session
2. backend creates player, session, and mastery state
3. frontend requests next puzzle or canonical game state
4. frontend renders returned state
5. player submits answer or gameplay action
6. backend validates, updates state, logs events, and returns canonical response

---

## 3. Backend Layering

### API Layer

Location:

- `backend/app/api/`

Responsibilities:

- validate request payloads
- translate HTTP requests into service calls
- return canonical envelope responses

The route layer must remain thin.

### Service Layer

Location:

- `backend/app/services/`

Responsibilities:

- session creation and progression
- puzzle delivery
- attempt orchestration
- gameplay action orchestration
- mastery integration
- telemetry event creation where appropriate

The service layer is the main home of business rules.

### Engine Layer

Location:

- `backend/app/engine/`

Responsibilities:

- BKT update logic
- adaptive difficulty policy
- content selector logic
- simulation helpers and engine-level testing

The engine layer must remain isolated from HTTP, UI, and ad hoc frontend concerns.

### Data Layer

Location:

- `backend/app/db/`

Responsibilities:

- database session setup
- model definitions
- migrations
- persistence compatibility

---

## 4. Frontend Layering

Location:

- `frontend/src/`

Key responsibilities:

- session creation UI
- puzzle rendering
- room scene rendering
- user input collection
- canonical API calls
- safe local interaction state
- graceful conflict recovery

### Frontend State Model

The frontend store should remain a mirror of server-derived state such as:

- `session_id`
- `condition`
- `current_level_index`
- `session_complete`
- current puzzle
- mastery snapshot
- last feedback
- canonical room and inventory state when gameplay v2 is active

### Local-only UI State

Allowed local-only state includes:

- active hotspot
- opened prompt
- answer text
- modal open/close state
- hover/focus/selection feedback
- temporary trace buffers
- dialogue animation progress

This preserves backend authority while keeping the UI responsive.

---

## 5. Canonical Ownership Model

### Backend owns

- progression order
- session completion
- puzzle scoring
- BKT updates
- gameplay v2 object, room, and inventory state
- canonical action/effect resolution

### Frontend owns

- rendering
- transport and retry behavior
- visual feedback
- accessibility behavior
- temporary UI state that does not alter canonical state

### Forbidden Frontend Ownership

Frontend must not:

- compute correctness
- compute mastery
- decide next skill or next room state
- mark a session complete
- commit canonical inventory/object state locally

---

## 6. Stable Modules to Preserve

These modules are considered strong foundations and should not be rewritten without strong justification.

### Backend app bootstrap and dependency wiring

- `backend/app/main.py`
- `backend/app/config.py`
- `backend/app/db/database.py`

### Backend domain engines

- `backend/app/engine/bkt_core.py`
- `backend/app/engine/bkt_params.py`
- `backend/app/engine/content_selector.py`
- `backend/app/engine/selector_types.py`

### Backend persistence core

- `backend/app/db/models.py`

### Frontend transport and reusable presentation layers

- `frontend/src/lib/api.ts`
- `frontend/src/lib/types.ts`
- reusable UI container components

Preserve these unless correctness or maintainability issues are proven.

---

## 7. Common Misalignment Risks

### Frontend-owned progression logic

This is a major validity and maintainability risk.

Progression must remain backend-owned.

### Skill-driven routing assumptions in the client

The client should not reconstruct progression by skill queries or phase branching when the backend already owns the sequence.

### Inconsistent telemetry semantics

Telemetry that changes shape or meaning without documentation undermines later analysis.

### Content/schema drift

If seed content, contracts, and tests drift apart, debugging becomes expensive and pilot confidence drops.

### Over-scoped frontend refactors

Large UI rewrites often reintroduce hidden gameplay authority into the client.

---

## 8. Additive Gameplay v2 Architecture

> **experimental — gameplay v2:** Proposal and implementation path for true room, object, inventory, and dialogue interactions. This does not replace canonical Phase-3 flow.

Gameplay v2 introduces:

- `GET /api/sessions/{session_id}/game-state`
- `POST /api/sessions/{session_id}/action`
- declarative `effects[]`
- canonical game snapshots
- typed payloads
- optional dedupe and stale-state handling

### Gameplay v2 Architectural Rules

- session mode is immutable
- v2 routes must reject non-v2 sessions
- v2 routes must reject requests when the global feature flag is disabled
- canonical attempts still route through `POST /attempts`
- telemetry remains observational
- backend applies effects atomically and returns canonical state after commit

### Forbidden Gameplay v2 Features

- client-side scripting interpreters
- executable effect scripts
- client-owned scoring or progression
- client-owned inventory mutation
- trace-driven scoring or adaptive policy changes

---

## 9. Concurrency, Dedupe, and Atomicity

Gameplay actions should be treated as transactional operations.

### Atomicity Rule

Backend should:

1. validate action preconditions
2. resolve effects
3. persist canonical changes
4. emit required telemetry
5. return committed canonical state

If validation fails, the action should not partially commit.

### Dedupe Rule

Clients may send `client_action_id`.

Dedupe scope should be:

- `(session_id, client_action_id)`

Safe duplicate replays may return the original success payload. Unsafe replays should return a machine-readable conflict response.

### Stale-state Rule

If `client_game_state_version` is stale, return `409` with canonical state for frontend reconciliation.

---

## 10. Architectural Guidance for Student Maintainers

Practical rules:

1. keep responsibilities clear
2. prefer one small vertical slice at a time
3. preserve backend authority
4. avoid large rewrites
5. document thresholds, event meaning, and flow rules centrally
6. align tests and docs with implementation rather than adding compatibility hacks
7. update both backend and frontend typed surfaces in one task when contracts change

---

## 11. Change Review Questions

Before approving an architectural change, ask:

1. does this move authority into the wrong layer
2. does it preserve backend-owned progression and scoring
3. does it break typed contracts
4. does it add undocumented telemetry semantics
5. does it preserve canonical Phase-3 behavior
6. is gameplay v2 still additive and feature-gated
7. is the change testable and documented

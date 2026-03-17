# Silent Frequency Repository Audit

Date: 2026-03-17
Prepared by: GitHub Copilot (GPT-5.3-Codex)

## Purpose
This document gives the team a practical audit of the current Silent Frequency codebase so you can plan Phase 2 refactoring safely.

The goal is to:
- protect experimental validity,
- improve architecture maintainability,
- and choose low-risk incremental changes later.

This phase is documentation only. No production code changes are proposed or implemented here.

## Audit Scope
In scope:
- backend architecture (FastAPI routes, services, BKT engine, selector, models)
- frontend architecture (page flow, state store, API layer, phase components)
- test/build health at a high level
- technical debt and refactoring priorities

Out of scope:
- implementing refactors
- adding features
- changing DB schema
- rewriting UI/UX

## Audit Method
Method used:
1. Reviewed repository structure and key modules in backend and frontend.
2. Traced live request flow from session creation to attempt submission.
3. Reviewed current logging paths for attempts and events.
4. Reviewed frontend progression logic in state/store and phase components.
5. Reviewed test/build status from prior audit runs.
6. Assessed technical debt against project goals:
   - fixed flow control,
   - backend-owned progression,
   - adaptive/static experimental integrity,
   - telemetry quality,
   - maintainable UI architecture.

Evidence basis:
- direct code inspection in backend/app and frontend/src
- existing test/build audit outcomes already captured in this repository

## Architecture Overview
Current architecture is a standard split:
- FastAPI backend with service layer + SQLAlchemy ORM
- Next.js frontend with Zustand client state
- BKT + content selection engines in backend
- relational puzzle/attempt/event persistence

High-level runtime flow:
1. Frontend creates session.
2. Backend creates player/session/mastery state.
3. Frontend asks backend for next puzzle item by skill.
4. Frontend submits answer.
5. Backend scores answer, updates BKT, logs attempt/event, returns updated mastery.

## Current Backend Design
### What works now
- Clean FastAPI entry structure in backend/app/main.py
- Thin API routes in backend/app/api/routes.py
- Service layer separation in backend/app/services
- BKT engine isolated in backend/app/engine/bkt_core.py
- Adaptive selector isolated in backend/app/engine/content_selector.py
- SQLAlchemy models cover players, sessions, mastery, puzzles, attempts, events

### Current behavior
- Session creation initializes SkillEstimate rows and GameState.
- Attempt submission updates mastery and writes to Attempt + EventLog.
- Selection is adaptive by mastery tier (low/mid/high).

### Key backend limitation
- Progression authority is not fully backend-owned yet. The frontend still drives skill/phase progression.

## Current Frontend Design
### What works now
- Clear app entry page and lobby flow in frontend/src/app/page.tsx
- Centralized client state in frontend/src/stores/gameStore.ts
- Thin API client wrappers in frontend/src/lib/api.ts
- Shared API/game types in frontend/src/lib/types.ts
- Reusable visual components (PuzzleContainer, GlitchText)

### Current behavior
- Frontend keeps phase and phaseIndex in Zustand.
- Frontend decides when to advance phase (based on p_learned_after threshold).
- Phase components repeat similar submit/feedback/next logic.

### Key frontend limitation
- Frontend currently contains progression logic, so it is not yet a dumb client.

## Working Modules To Preserve
Preserve these modules as stable foundations:

1. Backend app bootstrap and dependency injection
- backend/app/main.py
- backend/app/config.py
- backend/app/db/database.py

2. Backend domain engines
- backend/app/engine/bkt_core.py
- backend/app/engine/bkt_params.py
- backend/app/engine/content_selector.py
- backend/app/engine/selector_types.py

3. Backend persistence model core
- backend/app/db/models.py (especially SkillEstimate, Attempt, EventLog)

4. Frontend reusable presentation and transport layers
- frontend/src/components/PuzzleContainer.tsx
- frontend/src/components/GlitchText.tsx
- frontend/src/lib/api.ts
- frontend/src/lib/types.ts

These are good base pieces and do not require immediate replacement.

## Broken Or Misaligned Modules
Broken means currently failing operationally or blocking safe change. Misaligned means it works technically but conflicts with target architecture.

### Broken / blocking
1. Backend test execution environment
- Current issue: pytest collection failure due to missing aiosqlite in test environment.
- Impact: reduces confidence during refactoring.

### Misaligned with target design
1. Frontend-owned progression logic
- frontend/src/stores/gameStore.ts
- frontend/src/components/phases/VocabularyPhase.tsx
- frontend/src/components/phases/GrammarPhase.tsx
- frontend/src/components/phases/ListeningPhase.tsx
- Why misaligned: progression decisions are in client code.

2. Skill-driven route usage model
- backend/app/api/routes.py currently exposes next-item by explicit skill query.
- Why misaligned: backend should drive next step/scene in fixed flow.

3. Limited telemetry contract
- backend/app/services/session_service.py and puzzle_service.py log events, but taxonomy is minimal.
- Why misaligned: experimental analysis needs richer and consistent event semantics.

4. Puzzle authoring pipeline
- backend/app/seed.py holds puzzle content in Python constants.
- Why misaligned: maintainability improves when content is externalized (for later phase).

## Technical Debt Risks
Short risk register:

1. Frontend progression control biases experiment flow
- Severity: High
- Likelihood: High
- Risk type: Experimental validity

2. Missing explicit adaptive/static condition persistence
- Severity: High
- Likelihood: Medium-High
- Risk type: Experimental validity

3. Inconsistent telemetry payloads across events
- Severity: High
- Likelihood: Medium
- Risk type: Data quality and analysis reliability

4. Duplicate phase UI logic across three components
- Severity: Medium
- Likelihood: High
- Risk type: Maintainability and regression risk

5. Test environment instability on backend
- Severity: Medium
- Likelihood: Medium
- Risk type: Refactor safety

## Refactoring Priorities
Prioritized by:
1) experimental validity,
2) maintainable architecture,
3) low-risk incremental rollout.

### Priority P0 (do first)
Backend-owned progression contract
- Move next-step authority from frontend to backend decisions.
- Rationale: biggest validity risk and most central architecture issue.

### Priority P1
Server-side condition assignment (adaptive vs static)
- Persist condition at session level and carry through logs.
- Rationale: required for credible experimental comparison.

### Priority P2
Telemetry contract standardization
- Keep existing event_log table, but standardize event names and required payload keys.
- Rationale: protects analysis quality with low migration risk.

### Priority P3
Frontend phase logic consolidation
- Replace duplicated skill-specific puzzle interaction logic with one generic puzzle screen later.
- Rationale: maintainability improvement after backend authority is established.

### Priority P4
Puzzle content pipeline cleanup
- Move away from hardcoded seed constants over time.
- Rationale: useful but not first-order for experiment integrity.

## Recommended Next Phase
Phase 2 should start with one backend-first vertical slice.

Recommended sequence:
1. Define backend next-step decision for progression.
2. Keep current frontend screens, but render backend-decided progression state.
3. Persist adaptive/static condition on session and include in logs.
4. Standardize telemetry event contract for attempts and progression milestones.
5. Stabilize backend test environment before broader refactors.

Why this sequence:
- highest experimental risk is addressed first,
- architecture gets cleaner without a big-bang rewrite,
- frontend refactor can be incremental and safer.

## Maintenance Notes For A Student Team
Practical team guidance:

1. Keep responsibilities clear
- Backend decides game progression and experiment rules.
- Frontend displays state and collects user input.

2. Protect analytics quality
- Every event should have consistent naming and required fields.
- Do not add ad hoc payloads without agreed format.

3. Avoid large rewrites
- Make one change slice at a time and verify behavior with tests.

4. Preserve stable modules
- Do not rewrite BKT math or selector internals unless correctness issues are proven.

5. Track assumptions in docs
- Document thresholds, flow rules, and event meanings in one place.

6. Use a refactor checklist
- Before merging: flow correctness, telemetry completeness, and test pass status.

## Summary
Silent Frequency has a solid base architecture, but progression authority and experiment control are still split into the frontend. The safest path is backend-first progression control, explicit condition tracking, and telemetry standardization, followed by incremental frontend simplification.

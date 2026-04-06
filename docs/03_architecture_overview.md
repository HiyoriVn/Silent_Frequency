# Architecture Overview

## Architectural Principles

Silent Frequency follows a layered architecture:

- routes validate and delegate
- services implement business logic
- engine modules contain mastery and selection rules
- database and content layers provide persistence and authored content
- frontend mirrors backend-owned state and must not redefine core rules

## Backend Layering

### API Layer

Location:

- `backend/app/api/`

Responsibilities:

- validate request payloads
- map inputs to service calls
- return canonical API envelopes

Routes must remain thin.

### Service Layer

Location:

- `backend/app/services/`

Responsibilities:

- session creation and progression
- gameplay action orchestration
- attempt handling
- mastery updates
- puzzle delivery and business decisions

### Engine Layer

Location:

- `backend/app/engine/`

Responsibilities:

- BKT math
- adaptive difficulty policies
- content selection logic
- simulation support

This layer should stay independent from HTTP and UI concerns.

### Data Layer

Location:

- `backend/app/db/`

Responsibilities:

- model definitions
- database session setup
- migrations

## Frontend Structure

Location:

- `frontend/src/`

Responsibilities:

- render session state
- present puzzle phases
- display room and inventory state
- submit user actions and attempts
- recover gracefully from server conflict responses

The frontend must not become the authority for progression, completion, or mastery.

## Content System

Static content is currently organized under:

- `backend/app/content/puzzles/`
- `backend/app/content/rooms/`
- `backend/app/content/items/` when gameplay v2 item authoring is enabled

This supports deterministic seeding, testing, and research repeatability.

## Canonical Ownership Model

### Backend owns

- progression order
- session completion
- scoring
- BKT updates
- gameplay v2 canonical state transitions

### Frontend owns

- rendering
- local interaction UX
- transport and retry behavior
- non-canonical visual state such as hover, focus, and temporary animation

## Change Design Rule

Before implementing a feature, contributors should answer:

1. which layer owns the change
2. whether the API contract changes
3. whether frontend types must change
4. whether telemetry must change
5. whether canonical docs and tests must change

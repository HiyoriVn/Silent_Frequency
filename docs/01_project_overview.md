# Project Overview

## Purpose

Silent Frequency is an adaptive language-learning escape-room game. It combines structured puzzle progression with mastery-aware difficulty selection to support vocabulary, grammar, and listening practice.

## Product Goals

The project has two main goals:

1. deliver a working educational game prototype
2. support research and evaluation of adaptive gameplay and learning flow behavior

## Core Experience

A player session currently follows a backend-owned progression model in which:

- the backend creates and tracks the session
- the backend selects the next puzzle
- the frontend renders the returned state
- player attempts update mastery through the BKT engine
- optional gameplay v2 adds room/object/inventory interaction without replacing the canonical attempt flow

## Main Subsystems

### Backend

The backend is responsible for:

- session creation
- progression control
- puzzle selection
- answer scoring
- BKT mastery updates
- telemetry emission
- gameplay v2 action resolution

### Frontend

The frontend is responsible for:

- session start and user input
- puzzle rendering
- room and inventory interaction UI
- response submission
- feedback display
- graceful recovery from backend conflict responses

### Content Layer

The content layer stores:

- puzzle definitions
- room definitions
- item definitions
- seed data

### Research Layer

The research layer depends on:

- reproducible session flow
- telemetry collection
- pilot planning
- post-run analysis

## Repository Orientation

Important locations:

- `backend/app/api/`: thin route layer
- `backend/app/services/`: business logic
- `backend/app/engine/`: BKT and selection logic
- `backend/app/content/`: puzzle, room, and item content
- `backend/app/tests/`: backend feature tests
- `frontend/src/`: frontend implementation
- `frontend/tests/`: frontend interaction tests
- `tests/`: integration and legacy validation tests
- `scripts/`: operations scripts
- `docs/`: canonical documentation

## Contributor Expectations

Contributors should:

- prefer minimal, localized changes
- preserve backend ownership of progression and scoring
- keep frontend and backend contracts aligned
- update documentation whenever behavior changes
- validate changes through the relevant test path before merging

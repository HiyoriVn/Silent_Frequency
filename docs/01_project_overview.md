# Project Overview

## Purpose

Silent Frequency is an adaptive language-learning escape-room game prototype.

The current thesis prototype focuses on a single playable chapter that combines:

- room-based exploration
- object and clue interaction
- puzzle-driven English learning
- backend-owned mastery-aware adaptation

The project is intended both as:

1. an educational game prototype
2. a research artifact for studying adaptive gameplay and learning-flow behavior

## Product Goals

The project currently has two main goals:

1. deliver a stable single-chapter educational game prototype
2. support pilot-scale research and evaluation of adaptive gameplay, chapter flow, and learning support behavior

### Prototype Scope Rule

The thesis prototype prioritizes one polished playable chapter over a broad but incomplete multi-chapter implementation.

Additional chapters, expanded content banks, and broader mechanics remain future scope unless explicitly implemented and validated.

## Core Experience

A player session in the current thesis prototype is intended to follow this high-level experience:

1. player enters the game
2. player completes a short initialization or pre-test flow
3. player enters a room-based chapter
4. player explores zones, gathers clues, and interacts with objects
5. backend resolves gameplay actions and opens puzzle moments when conditions are met
6. puzzle attempts update mastery through the BKT engine
7. backend-owned adaptation adjusts later challenge or support behavior
8. player completes the chapter and receives a summary or post-run reflection

### Important Rule

The primary playable demo is chapter-based and room-driven.

The preserved Phase-3 fixed progression loop remains an important baseline for compatibility, testing, and research comparison, but is not the only intended user-facing flow.

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

### Chapter Design Layer

The current prototype also depends on a chapter-design layer that defines:

- zone structure
- interactable objects
- traversal logic
- puzzle gating conditions
- clue and inventory relationships
- narrative pacing inside the chapter

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
- preserve backend ownership of progression, scoring, and mastery
- keep frontend and backend contracts aligned
- preserve chapter coherence when adding new puzzles, objects, or zones
- reuse a small set of strong mechanics rather than expanding scope too broadly
- update documentation whenever behavior changes
- validate changes through the relevant test path before merging

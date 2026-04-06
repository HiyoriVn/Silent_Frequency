# Puzzle and Content System

## Overview

Silent Frequency uses file-based content for deterministic development and testing.

Current content roots:

- `backend/app/content/puzzles/`
- `backend/app/content/rooms/`
- `backend/app/content/items/` when gameplay v2 item definitions are used

## Puzzle Content

Each canonical learning puzzle should define:

- `puzzle_id`
- `skill`
- `slot_order`
- title and mechanic
- difficulty variants
- correct answer rules
- hint data
- display metadata required by the frontend

## Canonical Puzzle Rules

Each puzzle file should provide exactly three variants:

- `low`
- `mid`
- `high`

Tier rules:

- slot 1 is always `mid`
- static sessions always use `mid`
- adaptive sessions may use `low`, `mid`, or `high` on later slots

Keep the core mechanic constant across tiers. Only increase complexity by difficulty.

## Room and Item Content

Gameplay v2 content should remain declarative.

Room and item definitions may describe:

- scene assets
- objects
- hotspots
- item metadata
- puzzle links
- room interactions
- dialogue triggers

Do not embed executable logic in JSON content.

## Authoring Rules

When adding content:

1. use stable, lowercase snake_case IDs
2. avoid renaming shipped IDs
3. keep cross-file references valid
4. validate content locally before enabling it
5. do not hardcode content data in Python or frontend UI logic

## Runtime vs Authoring State

### Authoring files should contain

- stable definitions
- initial object state
- item reusability
- metadata needed for validation and rendering

### Runtime API snapshots may contain

- current inventory state
- current room state
- item consumption flags
- updated state versions

Do not mix authoring-only fields and runtime-only fields carelessly.

## Validation Expectations

Changes to puzzle or room content should trigger:

- seed validation
- room and item reference validation
- gameplay v2 flow tests when room/action behavior changes
- session flow review when canonical progression assumptions change

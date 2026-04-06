# Copilot Workflow

## Purpose

This document defines how to use VS Code and GitHub Copilot productively and safely in this repository.

The goal is not to let Copilot invent project behavior. The goal is to accelerate implementation while preserving existing contracts, architecture, and research validity.

## Working Rule

Before changing code, Copilot should be guided by:

1. `AGENTS.md`
2. the relevant file in `docs/`
3. the existing route -> service -> engine/frontend structure
4. the current tests in affected areas

## Recommended Task Flow

### 1. Frame the change

Ask Copilot to identify:

- whether the change affects canonical Phase-3 flow or gameplay v2
- which layer owns the change
- whether API contracts change
- whether telemetry changes
- which docs and tests are affected

### 2. Plan the impact

Ask Copilot to produce:

- a minimal file-change plan
- required backend changes
- required frontend type/client changes
- required test updates
- documentation updates

### 3. Build conservatively

Instruct Copilot to:

- keep routes thin
- place business logic in services
- keep BKT and selection logic in engine modules
- avoid reintroducing backend-owned rules into the frontend
- preserve typed payload and response handling

### 4. Review against contracts

Ask Copilot to review the diff for:

- contract drift
- test gaps
- telemetry mismatch
- frontend/backend alignment problems
- over-scoped or unnecessary refactors

### 5. Validate explicitly

Ask Copilot to generate the exact commands and checks needed before commit.

## Prompt Templates

### Contract-aware planning prompt

```text
Read AGENTS.md and the relevant docs file first.
Explain whether this change affects:
1. canonical Phase-3 flow
2. gameplay v2
3. API contracts
4. telemetry
5. frontend/backend type alignment

Then propose a minimal implementation plan.
```

### Safe implementation prompt

```text
Implement only the scoped change.
Keep backend routes thin.
Keep business logic in services and engine modules.
Do not move backend-owned progression or scoring logic into the frontend.
Update typed API surfaces if the response contract changes.
```

### Review prompt

```text
Review this change against the repository contracts.
Check for:
- backend/frontend mismatch
- undocumented API changes
- missing tests
- telemetry inconsistencies
- unnecessary architectural changes
Return blockers, warnings, and exact fixes.
```

## Definition of Done for Copilot-assisted Work

A Copilot-assisted change is complete only if:

- relevant docs are still accurate
- relevant tests were run
- contract alignment was checked
- scope remained controlled
- no hidden rule was moved into the wrong layer

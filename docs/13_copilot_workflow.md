<!-- CHANGELOG: pass-2 canonical rewrite preserving repo-aware workflow, contract discipline, and implementation guardrails -->

# Copilot Workflow

## Scope

This document defines how to use VS Code and GitHub Copilot productively and safely in this repository.

Its purpose is to accelerate implementation while preserving:

- architecture boundaries
- canonical contracts
- research validity
- testing discipline
- documentation quality

The goal is not to let Copilot invent system behavior.

---

## 1. Working Rule

Before changing code, Copilot should be guided by:

1. `AGENTS.md`
2. the relevant file in `docs/`
3. the current route -> service -> engine layering
4. the frontend state and typed API model
5. the existing tests in the affected area

Copilot should not be treated as an authority on system behavior unless grounded in these sources.

---

## 2. Copilot Usage Philosophy

Use Copilot to accelerate:

- implementation
- refactoring
- type alignment
- test drafting
- documentation updates
- review against contracts

Do not rely on Copilot to invent:

- undocumented API behavior
- hidden gameplay rules
- backend ownership changes
- scoring logic
- experimental assumptions

---

## 3. Required Task Flow

### Step 1 — Frame the Change

Ask Copilot to identify:

- whether the change affects canonical Phase-3 flow or gameplay_v2
- which layer owns the change
- whether API contracts change
- whether telemetry changes
- which docs and tests are affected

### Step 2 — Plan the Impact

Ask Copilot to produce:

- a minimal implementation plan
- required backend changes
- required frontend type/client changes
- required test updates
- required documentation updates

### Step 3 — Build Conservatively

Instruct Copilot to:

- keep routes thin
- place business logic in services
- keep BKT and selection logic in engine modules
- avoid moving backend-owned rules into frontend code
- preserve typed payload and response handling

### Step 4 — Review Against Contracts

Ask Copilot to review the change for:

- contract drift
- test gaps
- telemetry mismatches
- frontend/backend alignment issues
- over-scoped refactors
- hidden architectural shifts

### Step 5 — Validate Explicitly

Ask Copilot to generate:

- exact test commands to run
- docs that must be updated
- validation checks before commit
- known risks or blockers

---

## 4. Repo-specific Guardrails

### Canonical Phase-3 Guardrails

- do not reintroduce frontend-owned progression logic
- do not move scoring or completion logic into the client
- do not bypass `current_level_index`
- do not alter adaptive/static policy without updating tests and docs

### Gameplay v2 Guardrails

- treat gameplay_v2 as additive
- preserve feature-flag gating
- preserve immutable session mode
- keep `effects[]` declarative
- do not implement client-owned canonical mutations
- keep stale-state handling explicit and testable

### Telemetry Guardrails

- telemetry remains observational only
- trace data must not alter correctness or BKT
- do not invent new telemetry fields without documenting them
- preserve pilot QA thresholds where relevant

---

## 5. Recommended Prompt Templates

### Contract-aware planning prompt

```text
Read AGENTS.md and the relevant docs file first.
Explain whether this change affects:
1. canonical Phase-3 flow
2. gameplay_v2
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
Do not move backend-owned progression, scoring, or mastery logic into the frontend.
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

### Validation prompt

```text
Generate the exact validation checklist for this change.
Include:
- backend tests
- frontend tests
- contract alignment checks
- telemetry checks if applicable
- docs that must be updated
```

---

## 6. How Copilot Should Be Used in Specific Scenarios

### When changing backend routes

Copilot should:

- inspect current schema and service usage
- avoid embedding business logic in route handlers
- confirm response envelope compatibility
- update backend tests and frontend typed surfaces together

### When changing gameplay_v2 actions

Copilot should:

- preserve typed action payload structure
- preserve `interaction_schema_version`
- preserve conflict semantics
- preserve canonical attempt coexistence
- review telemetry implications

### When changing frontend puzzle UI

Copilot should:

- keep interaction state local when possible
- avoid adding puzzle-id-specific branching unless necessary
- avoid migrating canonical state rules into the client
- preserve accessibility behavior

### When changing content formats

Copilot should:

- preserve seed validation expectations
- preserve stable IDs
- avoid executable content logic
- identify required docs and tests that must change

---

## 7. Common Failure Modes When Using Copilot

Watch for these patterns:

- Copilot moving authority into the wrong layer
- Copilot silently changing API shape without updating types
- Copilot introducing gameplay logic into UI components
- Copilot over-refactoring stable modules
- Copilot adding telemetry fields without documentation
- Copilot solving test failures by weakening the tests instead of aligning implementation and docs

---

## 8. Required Review Questions Before Merge

Before merging a Copilot-assisted change, answer:

1. did the change preserve backend ownership
2. are contracts still documented correctly
3. were frontend types updated if needed
4. were relevant tests run
5. did telemetry meaning remain stable
6. is gameplay_v2 still additive and gated
7. did the change remain within scope

---

## 9. Definition of Done for Copilot-assisted Work

A Copilot-assisted change is complete only if:

- relevant docs are accurate
- relevant tests were run
- contract alignment was checked
- scope remained controlled
- no hidden rule was moved into the wrong layer
- telemetry implications were reviewed where relevant
- the result remains consistent with `AGENTS.md` and the canonical docs set

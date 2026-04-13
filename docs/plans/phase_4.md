# Phase 4 — Lightweight Adaptive Logic for Room 404

## 1. Goal

Introduce the first lightweight adaptive layer on top of the stable Room 404 puzzle loop.

At the end of this phase, the system should be able to:

- use `self_assessed_level` from Phase 1 as a warm-start signal
- maintain a minimal backend-owned mastery/adaptation state
- update that state after puzzle attempts
- use that state to influence at least one adaptive behavior in Room 404
- keep the existing Room 404 gameplay loop stable

This phase is not intended to implement a full CAT system.
It is intended to add a simple, testable adaptive runtime layer.

---

## 2. In Scope

- warm-start from `self_assessed_level`
- minimal mastery/adaptation state for gameplay_v2
- backend update after puzzle attempt
- minimal adaptive rule for Room 404
- support for low / mid / high tier or equivalent lightweight difficulty control
- support for simple hint/adaptive policy if needed
- Room 404 only

---

## 3. Out of Scope

- full psychometric CAT
- large-scale item calibration
- adaptive logic for all chapters
- full multi-skill mastery graph
- advanced analytics dashboards
- heavy UX redesign
- broad architecture refactor
- full battery/hint economy system
- full research-grade evaluation instrumentation

---

## 4. Required Inputs

Phase 4 must build on:

- Phase 1 onboarding/session self-assessment flow
- Phase 2 canonical Room 404 gameplay state
- Phase 3 puzzle loop and progression mutation
- the current puzzle/content data model
- the agreed adaptive direction:
  - simple
  - backend-owned
  - easy to test
  - not over-engineered

For this phase, Room 404 remains the only active adaptive testbed.

---

## 5. Adaptive Strategy for This Phase

### Design principle

Keep adaptation lightweight and deterministic.

### Recommended runtime approach

Use:

- self-assessment as warm-start
- backend-owned mastery estimate or difficulty bias
- simple mapping into:
  - puzzle tier selection
  - hint policy
  - or both

### Non-goals

Do not attempt to prove full CAT validity in this phase.
Do not build a large adaptive framework before one stable adaptive path exists.

---

## 6. Minimum Adaptive Scope

This phase only needs one stable adaptive loop.

### Minimum required loop

1. user starts session with `self_assessed_level`
2. backend maps it into initial adaptive state
3. user attempts `p_warning_sign_translate`
4. backend updates adaptive state after result
5. next relevant Room 404 puzzle-facing behavior can reflect that adaptive state

### Acceptable first adaptive outputs

At least one of:

- choose `low / mid / high` puzzle variant by backend state
- expose a simple `hint_policy`
- expose a simple `difficulty_tier`
- expose a simple mastery status for the Room 404 skill tag

---

## 7. Batches

## Batch 4.1 — Warm-start mapping from self-assessment

### Goal

Map Phase 1 self-assessment into an initial backend adaptive state.

### Tasks

- define minimal mapping from `self_assessed_level`
- initialize adaptive state in gameplay/session context
- keep logic simple and deterministic

### Allowed files

- backend session/adaptive state files
- backend schemas/types if needed
- `docs/output/phase_4.md`

### Do not touch

- full puzzle evaluation logic beyond initialization needs
- broad frontend redesign
- full CAT engine
- later chapter zones

### Done criteria

- new session has a clear initial adaptive state
- mapping is stable and documented
- no broad refactor is introduced

---

## Batch 4.2 — Backend update after puzzle attempt

### Goal

Update the adaptive/mastery state after puzzle result.

### Tasks

- hook into the result of `p_warning_sign_translate`
- update minimal adaptive state
- keep the update backend-owned
- keep it deterministic and testable

### Allowed files

- backend puzzle/adaptive/session state files
- backend schemas if needed
- `docs/output/phase_4.md`

### Do not touch

- broad scoring redesign
- later chapter puzzles
- frontend-heavy UX changes

### Done criteria

- correct/incorrect puzzle result updates adaptive state
- state can be inspected in backend/game-state response or equivalent
- no unrelated refactor is introduced

---

## Batch 4.3 — Minimal adaptive output contract

### Goal

Expose the minimum adaptive output needed for Room 404 behavior.

### Tasks

- expose one or more of:
  - `difficulty_tier`
  - `hint_policy`
  - lightweight mastery tag/status
- keep this contract backend-owned
- make it usable by frontend or next puzzle flow

### Allowed files

- backend schemas/services
- frontend types only if needed
- `docs/output/phase_4.md`

### Do not touch

- broad UI redesign
- full adaptive dashboards
- unrelated docs

### Done criteria

- adaptive output is available in a stable contract
- later puzzle flow can consume it safely
- Room 404 loop remains stable

---

## Batch 4.4 — Apply adaptive behavior to next Room 404 puzzle-facing path

### Goal

Use the adaptive state to influence an actual Room 404 behavior.

### Tasks

Apply adaptation to at least one of:

- variant/tier selection for the next puzzle-facing content
- hint policy behavior
- prompt difficulty selection

### Allowed files

- backend puzzle/adaptive services
- frontend puzzle UI only if needed to display the chosen behavior
- `docs/output/phase_4.md`

### Do not touch

- full multi-puzzle expansion
- full chapter adaptive rollout
- broad refactors

### Done criteria

- at least one visible or inspectable adaptive behavior now depends on backend adaptive state
- behavior remains deterministic and testable
- no regression to the existing puzzle loop

---

## Batch 4.5 — Minimal adaptive feedback / observability

### Goal

Make the adaptive behavior visible enough for testing without overbuilding UX.

### Tasks

- add minimal adaptive observability for testers/devs
- acceptable examples:
  - adaptive debug line
  - tier/hint policy label
  - lightweight status panel entry
- keep it temporary and minimal

### Allowed files

- frontend UI files
- backend schema/types only if needed
- `docs/output/phase_4.md`

### Do not touch

- polished final UX
- full analytics UI
- broad app redesign

### Done criteria

- tester/dev can verify that adaptation changed something
- no heavy UI work is introduced
- current Room 404 flow remains stable

---

## 8. API Expectations

By the end of Phase 4, the system should support:

- initial adaptive state derived from self-assessment
- backend adaptive state update after puzzle attempts
- at least one stable adaptive output contract
- at least one applied adaptive behavior in Room 404

---

## 9. Expected Deliverables

At the end of Phase 4, the repo should contain:

- warm-start mapping from self-assessment
- minimal adaptive/mastery state
- backend update after puzzle result
- one stable adaptive output contract
- one Room 404 behavior that actually uses adaptive state
- minimal adaptive visibility for testing

---

## 10. Done Criteria for Phase 4

Phase 4 is complete only if:

- self-assessment influences initial adaptive state
- adaptive state updates after puzzle attempts
- at least one Room 404 behavior uses adaptive state
- the result is testable and visible enough for validation
- the existing Room 404 loop does not regress

---

## 11. Risks to Avoid

- overbuilding a full CAT framework too early
- spreading adaptive logic across frontend and backend
- hiding adaptive changes so testers cannot verify them
- introducing multiple adaptive rules at once
- destabilizing the Room 404 puzzle loop
- expanding to other zones before one adaptive path is proven stable

---

## 12. Manual Test Guide

### Test 1 — Warm-start

1. create two new sessions with different `self_assessed_level` values
2. confirm initial adaptive state differs as expected

### Test 2 — Update after attempt

1. solve or fail `p_warning_sign_translate`
2. confirm adaptive state changes after the attempt

### Test 3 — Adaptive behavior

1. inspect the next Room 404 puzzle-facing path
2. confirm one visible or inspectable behavior depends on adaptive state

### Test 4 — No regression

1. run the standard Room 404 loop
2. confirm trigger, modal, answer submit, progression, and feedback still work

---

## 13. Completion Log Template

When Codex completes this phase, add a completion block to `docs/output/phase_4.md`:

### Implementation completion log

- date:
- owner:
- Codex version/mode used:
- files changed:
- endpoints added/updated:
- schemas changed:
- tests run:
- manual test result:
- blockers remaining:
- notes for Phase 5:

---

## 14. Suggested Prompt Strategy for Codex

Do not ask Codex to implement all of Phase 4 at once.

Run it batch by batch:

- Batch 4.1
- Batch 4.2
- Batch 4.3
- Batch 4.4
- Batch 4.5

Each prompt should:

- ask Codex to read this phase doc first
- scope to one batch only
- list allowed files
- list do-not-touch areas
- require a file-change summary
- require manual test steps
- require output log update

---

## 15. Condition to Move to Phase 5

Only move to Phase 5 when:

- one stable adaptive path exists in Room 404
- adaptive state is initialized and updated correctly
- at least one Room 404 behavior clearly uses that state
- the overall gameplay loop remains stable

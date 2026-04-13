# Phase 3 — Puzzle Modal and Progression for Room 404

## 1. Goal

Implement the first end-to-end puzzle and progression loop for the Room 404 vertical slice.

At the end of this phase, a tester should be able to:

- enter the Room 404 vertical slice from the existing Phase 1 and Phase 2 flow
- trigger at least one Room 404 puzzle from a hotspot
- see a puzzle modal or equivalent puzzle interaction surface
- submit an answer
- receive correct / incorrect feedback
- update canonical backend-owned state after puzzle completion
- unlock at least one progression effect in Room 404

This phase turns the Room 404 slice from a navigation prototype into an actual playable puzzle loop.

---

## 2. In Scope

- puzzle trigger flow for Room 404
- minimal puzzle modal or equivalent puzzle UI
- one end-to-end puzzle implementation for:
  - `p_warning_sign_translate`
- optional early support for:
  - `p_patient_chart_keyword`
  - `p_room404_locker_code`
    if trivial and low-risk
- answer submission flow
- correct/incorrect feedback
- backend-owned progression updates after success
- minimal journal/inventory/progression state updates after puzzle success
- minimal frontend rendering of puzzle result/effects
- locked/unlocked state transition for Room 404 progression

---

## 3. Out of Scope

- full chapter puzzle integration
- Nurse Station puzzle chain
- Security Office puzzle chain
- full BKT tuning
- multi-puzzle adaptive selection system
- hint economy/battery economy
- polished puzzle art
- final journal UX
- full analytics/telemetry pass
- broad gameplay refactor
- broad frontend redesign

---

## 4. Required Inputs

Phase 3 must follow:

- current Phase 1 onboarding/session flow
- current Phase 2 Room 404 vertical slice
- current canonical game-state read model and mutation path
- current Room 404 hotspot IDs and canonical actions
- agreed puzzle bank/content sheet structure
- agreed Room 404 puzzle mapping

Primary puzzle for this phase:

- `p_warning_sign_translate`

Primary Room 404 progression effect:

- set or confirm `first_language_interaction_done`
- optionally update another progression flag if needed
- prepare or unlock downstream Room 404 progress path

---

## 5. Minimum Room 404 Puzzle Scope

This phase only needs one complete puzzle loop to be considered successful.

### Minimum required puzzle

- `p_warning_sign_translate`

### Minimum required trigger

- hotspot: `warning_sign`

### Minimum required effect

- open puzzle interaction surface
- submit answer
- evaluate answer
- apply success effects to canonical state
- reflect changes in subsequent game-state fetch / frontend UI

### Minimum expected loop

1. user enters Room 404
2. user clicks `warning_sign`
3. backend returns puzzle-open effect or equivalent
4. frontend opens puzzle modal
5. user answers
6. backend evaluates answer
7. backend updates canonical state
8. frontend receives updated state/effects
9. room progression changes accordingly

---

## 6. Batches

## Batch 3.1 — Puzzle trigger binding

### Goal

Bind Room 404 hotspot-triggered puzzle opening to a canonical flow.

### Tasks

- ensure `warning_sign` interaction can trigger puzzle opening
- keep canonical hotspot/action flow
- return an effect or payload that frontend can use to open the puzzle UI
- keep trigger path backend-owned

### Allowed files

- backend action/game service files
- backend schemas if required
- frontend API/types only if needed for trigger handling
- `docs/output/phase_3.md`

### Do not touch

- full puzzle scoring engine unless needed
- full BKT logic
- other chapter zones
- unrelated onboarding/session code
- broad refactors

### Done criteria

- `warning_sign` interaction can open the intended puzzle flow
- frontend receives enough information to show puzzle UI
- no unrelated architectural change is introduced

### Manual test

1. enter Room 404
2. click `warning_sign`
3. confirm puzzle-open effect or equivalent response is produced
4. confirm frontend can recognize it

---

## Batch 3.2 — Puzzle modal or puzzle interaction surface

### Goal

Implement the minimal frontend UI needed to present and answer the puzzle.

### Tasks

- add or adapt a minimal puzzle modal / panel
- display:
  - title
  - prompt text
  - answer input or choice UI
  - optional basic hint display if already supported
- allow submit
- allow close/cancel only if compatible with current flow

### Allowed files

- frontend puzzle UI/component files
- frontend API helpers/types
- minimal local UI state for puzzle rendering
- `docs/output/phase_3.md`

### Do not touch

- broad frontend redesign
- final polished puzzle UX
- unrelated scene rendering logic
- other chapter puzzle flows

### Done criteria

- puzzle UI opens for Room 404 warning sign
- user can read prompt
- user can submit an answer
- frontend can handle loading/result states without crashing

### Manual test

1. open Room 404 puzzle
2. confirm modal/panel appears
3. enter an answer
4. confirm submit works

---

## Batch 3.3 — Answer submission and evaluation

### Goal

Implement the minimal backend answer-checking path for the first Room 404 puzzle.

### Tasks

- support answer submission for `p_warning_sign_translate`
- evaluate correct vs incorrect answer
- return canonical result/effects
- preserve backend ownership of evaluation
- keep implementation aligned with current puzzle/content structures

### Allowed files

- backend puzzle evaluation / action / attempt files
- backend schemas/services
- frontend API/types if needed for answer submit
- `docs/output/phase_3.md`

### Do not touch

- full adaptive selector
- later puzzle bank expansion
- unrelated chapter puzzles
- broad scoring refactor

### Done criteria

- correct answer is accepted
- incorrect answer is rejected with clear feedback
- response is deterministic and backend-owned
- no unrelated puzzle systems are expanded unnecessarily

### Manual test

1. submit wrong answer
2. confirm failure feedback
3. submit correct answer
4. confirm success feedback

---

## Batch 3.4 — Progression effects and Room 404 unlock state

### Goal

Apply canonical progression effects after puzzle success.

### Tasks

- apply `success_effects` or equivalent canonical update
- update at least:
  - `first_language_interaction_done`
- if current Room 404 progression requires it, also unlock a downstream state
- ensure subsequent game-state fetch reflects the updated flags/state
- ensure frontend updates visibly after success

### Allowed files

- backend action/puzzle/game-state mutation files
- backend schemas if needed
- frontend read/update flow only if required to reflect the new state
- `docs/output/phase_3.md`

### Do not touch

- full chapter progression
- other zones
- BKT internals unless absolutely required
- unrelated docs
- broad architecture changes

### Done criteria

- solving the puzzle updates canonical state
- updated flags are visible in game-state fetch
- frontend state reflects the unlock or progression change
- no crash occurs after success

### Manual test

1. solve `p_warning_sign_translate`
2. fetch or observe updated game state
3. confirm progression flag changed
4. confirm room behavior changes accordingly if applicable

---

## Batch 3.5 — Minimal journal/inventory/progression feedback

### Goal

Provide the minimum visible feedback so testers can tell progression actually happened.

### Tasks

- show at least one of the following after puzzle success:
  - updated room feedback
  - updated last-effects area
  - updated journal entry list
  - updated clue/progression status
- keep UX minimal
- avoid building the full journal system too early

### Allowed files

- frontend Room 404 / puzzle UI files
- frontend display helpers
- `docs/output/phase_3.md`

### Do not touch

- polished journal redesign
- full inventory UX overhaul
- other chapter zones
- broad UI refactors

### Done criteria

- tester can clearly see that puzzle completion changed game state
- feedback is visible in browser without API inspection only
- no unnecessary UI complexity is introduced

### Manual test

1. solve the puzzle
2. confirm visible progression feedback appears
3. confirm user can continue interacting with the room

---

## 7. API Expectations

By the end of Phase 3, the system should support:

### Read path

- canonical `GET /game-state` from Phase 2

### Action trigger path

- Room 404 hotspot trigger that opens puzzle flow

### Puzzle submit path

- canonical backend answer evaluation for at least one Room 404 puzzle

### Post-success state update

- canonical state mutation after puzzle success
- frontend-visible progression feedback

---

## 8. Expected Deliverables

At the end of Phase 3, the repo should contain:

- one working Room 404 puzzle trigger flow
- one working puzzle interaction UI
- one working answer submission path
- one working backend evaluation path
- one working progression update after success
- one visible frontend feedback loop after puzzle completion

---

## 9. Done Criteria for Phase 3

Phase 3 is complete only if:

- `warning_sign` can trigger a puzzle interaction
- puzzle UI opens correctly
- user can submit an answer
- backend evaluates correct/incorrect answer
- canonical state changes after success
- frontend visibly reflects progression after success
- the Room 404 vertical slice remains stable and does not regress

---

## 10. Risks to Avoid

- implementing all Room 404 puzzles at once
- mixing puzzle evaluation logic into frontend-only code
- bypassing canonical state updates
- overbuilding journal/inventory UX too early
- introducing BKT complexity before one stable puzzle loop exists
- refactoring gameplay architecture too broadly during a narrow puzzle phase

---

## 11. Manual Test Guide

### Test 1 — Trigger puzzle

1. complete Phase 1 flow
2. enter Room 404
3. click `warning_sign`
4. confirm puzzle interaction opens

### Test 2 — Wrong answer

1. open the warning sign puzzle
2. submit an incorrect answer
3. confirm clear incorrect feedback appears
4. confirm no unintended unlock occurs

### Test 3 — Correct answer

1. open the warning sign puzzle
2. submit the correct answer
3. confirm success feedback appears
4. confirm canonical progression state updates

### Test 4 — Visible room feedback after success

1. solve the puzzle
2. return to room view if needed
3. confirm visible progression feedback appears
4. confirm room interaction remains stable

---

## 12. Completion Log Template

When Codex completes this phase, add a completion block to `docs/output/phase_3.md`:

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
- notes for Phase 4:

---

## 13. Suggested Prompt Strategy for Codex

Do not ask Codex to implement all of Phase 3 at once.

Run it batch by batch:

- Batch 3.1
- Batch 3.2
- Batch 3.3
- Batch 3.4
- Batch 3.5

Each prompt should:

- ask Codex to read this phase doc first
- scope to one batch only
- list allowed files
- list do-not-touch areas
- require a file-change summary
- require manual test steps
- require output log update

---

## 14. Condition to Move to Phase 4

Only move to Phase 4 when:

- one Room 404 puzzle loop is stable end-to-end
- puzzle trigger, answer submission, and progression update all work
- frontend can visibly show puzzle completion effect
- no blocker regression appears in the Room 404 vertical slice

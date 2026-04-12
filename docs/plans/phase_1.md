# Phase 1 — Onboarding and Session

## Goal

Implement the minimum onboarding and session flow required to start the Chapter 1 prototype.

At the end of this phase, a tester should be able to:

- register
- log in
- log out
- choose a quick self-assessed English level
- create a gameplay session
- enter the initial game shell or pre-game state

---

## In Scope

- minimal user model
- register endpoint and UI
- login endpoint and UI
- logout behavior
- quick self-assessment selection
- session creation for the chapter prototype
- initial session payload
- initial placeholder game shell entry

---

## Out of Scope

- password reset
- email verification
- social login
- advanced profile settings
- full pre-test implementation
- Room 404 rendering
- gameplay_v2 action resolver
- puzzle modal flow
- full BKT update logic
- adaptive puzzle selection
- unrelated refactors

---

## Required Inputs

This phase should follow the current canonical project docs and the agreed chapter prototype direction.

Required fields for onboarding/session init:

- `username`
- `password`
- `real_name`
- `school_level` or `grade`
- `self_assessed_level`
- optional `self_assessed_confidence`
- `condition`
- `mode`

---

## Batches

### Batch 1.1 — Minimal auth

Implement:

- user model fields required for internal testing
- register flow
- login flow
- logout flow
- password hashing

Done criteria:

- a new user can register
- a valid user can log in
- invalid password is rejected
- logout clears client auth state

### Batch 1.2 — Quick self-assessment

Implement:

- onboarding UI for quick self-assessment
- persist `self_assessed_level`
- optionally persist `self_assessed_confidence`

Suggested labels:

- `beginner`
- `elementary`
- `intermediate`
- `upper_intermediate`

Done criteria:

- user must choose one level before starting session
- value is included in session init payload
- persisted value is visible in backend session context

### Batch 1.3 — Session creation

Implement:

- session creation endpoint for chapter prototype
- support `condition`
- support `mode`
- support `self_assessed_level`
- initialize minimal game/session context

Response should include at least:

- `session_id`
- `mode`
- `condition`
- `self_assessed_level`
- initial placeholder game/session state reference

Done criteria:

- session is created successfully
- response returns a valid `session_id`
- frontend can transition into the next app state

### Batch 1.4 — Frontend entry flow

Implement:

- register/login entry flow
- self-assessment step
- start session action
- transition into game shell placeholder

Done criteria:

- the user can go from app entry to initial game shell without manual API calls
- no gameplay logic is hardcoded into onboarding

---

## Allowed Files

Codex may update files related to:

- auth models
- auth routes/schemas/services
- session routes/schemas/services
- frontend auth/session entry flow
- frontend API client/types for onboarding/session start

---

## Do Not Touch

Do not modify:

- gameplay_v2 scene rendering
- Room 404 interaction logic
- hotspot/action resolver
- puzzle modal implementation
- BKT engine internals
- unrelated docs or broad architecture

---

## Done Criteria for Phase 1

Phase 1 is complete only if:

- register works
- login works
- logout works
- quick self-assessment works
- session creation returns a valid `session_id`
- frontend reaches a game shell or equivalent placeholder state
- changes remain localized
- no unrelated refactor is introduced

---

## Manual Test Guide

### Test 1 — Register

1. Open the app.
2. Go to register.
3. Create a new account.
4. Confirm success.

### Test 2 — Login / logout

1. Log in with the new account.
2. Confirm success.
3. Log out.
4. Confirm client auth state is cleared.

### Test 3 — Self-assessment

1. Log in.
2. Select one self-assessed level.
3. Submit.
4. Confirm the selected level is sent to backend.

### Test 4 — Session creation

1. Complete onboarding.
2. Start session.
3. Confirm response includes `session_id`, `mode`, and `condition`.
4. Confirm app transitions into initial game shell or equivalent placeholder state.

---

## Expected Deliverables

- working auth flow
- self-assessment flow
- session creation flow
- initial placeholder game-shell entry
- short implementation summary
- manual test results
- list of remaining blockers for Phase 2

<!-- CHANGELOG: pass-2 canonical rewrite preserving test layers, commands, E2E flow, and gameplay_v2 QA details -->

# Testing Strategy

## Scope

This document defines the recommended validation strategy for Silent Frequency.

It covers:

- unit tests
- integration tests
- frontend tests
- manual E2E validation
- gameplay v2 QA
- definition of done

---

## 1. Testing Goals

The test strategy exists to ensure that:

- canonical session flow remains stable
- backend-owned progression remains correct
- gameplay v2 behavior is safe and recoverable
- telemetry contracts remain valid
- frontend and backend stay aligned

---

## 2. Test Layers

### Unit Tests

Use unit tests for:

- BKT logic
- content selection
- schema validation
- isolated service behavior
- action and effect mapping

### Integration Tests

Use integration tests for:

- API endpoint behavior
- session progression
- gameplay v2 flows
- telemetry creation
- dedupe and stale-state handling

### Frontend Tests

Use frontend tests for:

- rendering behavior
- user interactions
- stale-state recovery behavior
- hint and trace-related UI behavior
- accessibility-sensitive interaction flow

### Manual E2E Validation

Use manual E2E checks for:

- full loop verification
- environment sanity checks
- staging or demo validation
- pilot readiness checks

---

## 3. Recommended Commands

### Backend Engine Tests

```bash
python -m pytest backend/app/engine/test_bkt.py -v
python -m pytest backend/app/engine/test_content_selector.py -v
```

### Backend Feature Tests

```bash
python -m pytest backend/app/tests -v
python -m pytest tests/test_api_endpoints.py -v
python -m pytest tests/test_bkt_extended.py -v
```

### Gameplay v2-focused Backend QA

```bash
python -m pytest -q \
   backend/app/tests/test_attempt_from_gameplay_v2.py \
   backend/app/tests/test_hint_count_and_trace_backend.py \
   backend/app/tests/test_trace_trimming_metrics.py \
   backend/app/tests/test_game_action_telemetry_exists.py
```

### Frontend Validation

```bash
cd frontend
npm run lint
npm run test
```

### Gameplay v2-focused Frontend QA

```bash
cd frontend && npm run test -- \
   tests/PuzzleScreen.409.test.tsx \
   tests/HintPanel.test.tsx \
   tests/Trace.cap.test.tsx
```

---

## 4. Manual E2E Validation for Canonical Session Loop

This guide verifies the full backend session loop:

1. create session
2. get next puzzle
3. submit attempt
4. repeat until complete

### Prerequisites

1. backend is running:

```bash
uvicorn backend.app.main:app --reload
```

2. seed data is loaded:

```bash
python -m backend.app.seed
```

### 1) Create Session

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"display_name":"E2E Tester","condition":"adaptive"}'
```

Expected:

- `ok: true`
- `data.session_id` present
- `data.current_level_index = 0`
- `data.mastery` includes vocabulary, grammar, and listening

### 2) Get Next Puzzle

```bash
curl http://localhost:8000/api/sessions/<SESSION_ID>/next-puzzle
```

Expected:

- `ok: true`
- contains `puzzle_id`, `variant_id`, `skill`, `slot_order`
- first slot returns `difficulty_tier: "mid"`
- `session_complete: false`

### 3) Submit Attempt

```bash
curl -X POST http://localhost:8000/api/sessions/<SESSION_ID>/attempts \
  -H "Content-Type: application/json" \
  -d '{
    "variant_id":"<VARIANT_ID>",
    "answer":"sample answer",
    "response_time_ms":2200,
    "hint_count_used":0
  }'
```

Expected:

- `ok: true`
- contains `is_correct`, `correct_answers`, `p_learned_before`, `p_learned_after`
- returns `current_level_index` incremented by 1

### 4) Repeat Until Complete

Loop `next-puzzle -> attempts` until:

- `next-puzzle` returns `session_complete: true`

Expected progression count:

- 9 puzzle steps total

### Verify Progression Order

1. vocabulary slot 1
2. vocabulary slot 2
3. vocabulary slot 3
4. grammar slot 1
5. grammar slot 2
6. grammar slot 3
7. listening slot 1
8. listening slot 2
9. listening slot 3

### Verify Adaptive Difficulty

For `adaptive` sessions:

- slot 1 should be `mid`
- later slots should vary by BKT mastery state

For comparison, create a `static` session and verify all tiers remain `mid`.

### Verify Mastery Updates

Call mastery endpoint between attempts:

```bash
curl http://localhost:8000/api/sessions/<SESSION_ID>/mastery
```

Expected:

- `update_count` increases after each attempt for attempted skill
- `p_learned` values change over time

---

## 5. Optional JS Fetch Example for Manual Loop

```javascript
const base = "http://localhost:8000";
const create = await fetch(`${base}/api/sessions`, {
  method: "POST",
  headers: { "Content-Type": "application/json" },
  body: JSON.stringify({ display_name: "E2E Tester", condition: "adaptive" }),
}).then((r) => r.json());

const sessionId = create.data.session_id;
let done = false;

while (!done) {
  const next = await fetch(
    `${base}/api/sessions/${sessionId}/next-puzzle`,
  ).then((r) => r.json());

  if (next.data.session_complete) {
    done = true;
    break;
  }

  await fetch(`${base}/api/sessions/${sessionId}/attempts`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      variant_id: next.data.variant_id,
      answer: "sample answer",
      response_time_ms: 1500,
      hint_count_used: 0,
    }),
  });
}
```

---

## 6. Gameplay v2 Validation Expectations

When gameplay v2 changes are involved, also verify:

- `GET /game-state` returns canonical snapshots
- `POST /action` returns typed effects
- stale-state handling produces recoverable UI behavior
- duplicate `client_action_id` behavior is safe
- telemetry is emitted with expected fields
- canonical `POST /attempts` flow remains intact

### Minimum Gameplay v2 QA Checklist

1. create a gameplay v2 session
2. fetch the initial canonical snapshot
3. resolve at least one action successfully
4. verify `effects[]` and updated canonical state
5. verify `open_puzzle` still routes scoring through canonical attempts
6. test a stale-state `409` path
7. confirm telemetry appears
8. confirm no regression in Phase-3 canonical endpoints

---

## 7. Common Failure Pattern: Phase-3 Seed/Content Mismatch

Failures in `tests/test_api_endpoints.py` may occur from seed/content mismatch.

### How to Reproduce

```bash
python -m pytest tests/test_api_endpoints.py -v
```

### Where to Inspect

1. `backend/app/seed.py`
2. `backend/app/content/`
3. `backend/app/services/puzzle_service.py`
4. `backend/app/api/routes.py`

### Common Causes

- expected route contract differs from implemented endpoint shape
- seed content IDs no longer align with fixtures
- old test assumptions about skill/slot flow diverge from backend-owned progression

---

## 8. Definition of Done

A change is not complete until:

- relevant automated tests pass
- impacted manual checks are documented
- docs are updated
- frontend/backend contract alignment is confirmed
- telemetry implications are reviewed when event or trace behavior changes

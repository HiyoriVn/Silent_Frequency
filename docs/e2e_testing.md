# E2E Manual Testing

This guide verifies the full backend session loop:

1. create session
2. get next puzzle
3. submit attempt
4. repeat until complete

## Prerequisites

1. Backend is running (`uvicorn backend.app.main:app --reload`).
2. Seed data loaded (`python -m backend.app.seed`).

## 1) Create Session

```bash
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"display_name":"E2E Tester","condition":"adaptive"}'
```

Expected:

- `ok: true`
- `data.session_id` present
- `data.current_level_index = 0`
- `data.mastery` has vocabulary/grammar/listening

## 2) Get Next Puzzle

```bash
curl http://localhost:8000/api/sessions/<SESSION_ID>/next-puzzle
```

Expected:

- `ok: true`
- contains `puzzle_id`, `variant_id`, `skill`, `slot_order`
- first slot returns `difficulty_tier: "mid"`
- `session_complete: false`

## 3) Submit Attempt

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

## 4) Repeat Until Complete

Loop `next-puzzle -> attempts` until:

- `next-puzzle` returns `session_complete: true`

Expected progression count:

- 9 puzzle steps total

## Verify Progression Works

Check that skills and slot order follow backend script:

1. vocabulary slot 1
2. vocabulary slot 2
3. vocabulary slot 3
4. grammar slot 1
5. grammar slot 2
6. grammar slot 3
7. listening slot 1
8. listening slot 2
9. listening slot 3

## Verify Adaptive Difficulty

For `adaptive` sessions:

- slot 1 should be `mid`
- later slots should vary by BKT mastery state (`low`, `mid`, `high`)

For comparison, create a `static` session and verify all tiers remain `mid`.

## Verify Mastery Updates

Call mastery endpoint between attempts:

```bash
curl http://localhost:8000/api/sessions/<SESSION_ID>/mastery
```

Expected:

- `update_count` increases after each attempt for attempted skill
- `p_learned` values change over time

## Optional Fetch Example

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

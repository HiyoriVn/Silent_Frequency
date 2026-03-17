# Silent Frequency — QA Test Plan

> **Version:** 1.0  
> **Date:** 2026-03-01  
> **System under test:** Backend (FastAPI + BKT engine) + Frontend (Next.js + GlitchText)

---

## Table of Contents

1. [Test Cases — BKT Update](#1-test-cases--bkt-update)
2. [Test Cases — Adaptive Difficulty](#2-test-cases--adaptive-difficulty)
3. [Test Cases — API Endpoints](#3-test-cases--api-endpoints)
4. [Test Cases — Glitch Rendering](#4-test-cases--glitch-rendering)
5. [Edge Case Scenarios](#5-edge-case-scenarios)
6. [Example API Test Calls](#6-example-api-test-calls)
7. [Failure Handling Strategies](#7-failure-handling-strategies)

---

## 1. Test Cases — BKT Update

Implementation: `backend/app/engine/bkt_core.py`  
Test files: `backend/app/engine/test_bkt.py` (32 unit tests) + `tests/test_bkt_extended.py` (24 extended tests)

### 1.1 Posterior Update — Correct Answer

| ID      | Test Case            | Input                                  | Expected                           | Status |
| ------- | -------------------- | -------------------------------------- | ---------------------------------- | ------ |
| BKT-C01 | Basic correct update | P(L)=0.1, P(S)=0.1, P(G)=0.25, correct | P(L\|correct) ≈ 0.2857             | ✅     |
| BKT-C02 | High-mastery correct | P(L)=0.95, correct                     | Posterior > 0.95                   | ✅     |
| BKT-C03 | Zero-mastery correct | P(L)=0.0, correct                      | Posterior = 0.0 (all guessing)     | ✅     |
| BKT-C04 | No-guessing correct  | P(G)=0.0, correct                      | Posterior = 1.0 (proves knowledge) | ✅     |
| BKT-C05 | High-guess correct   | P(G)=0.90, correct                     | Posterior increase minimal         | ✅     |

### 1.2 Posterior Update — Incorrect Answer

| ID      | Test Case              | Input                                    | Expected                              | Status |
| ------- | ---------------------- | ---------------------------------------- | ------------------------------------- | ------ |
| BKT-I01 | Basic incorrect update | P(L)=0.1, P(S)=0.1, P(G)=0.25, incorrect | P(L\|incorrect) ≈ 0.0146              | ✅     |
| BKT-I02 | High-mastery incorrect | P(L)=0.95, incorrect                     | Posterior < 0.95                      | ✅     |
| BKT-I03 | No-slip incorrect      | P(S)=0.0, incorrect                      | Posterior = 0.0 (proves no knowledge) | ✅     |
| BKT-I04 | High-slip incorrect    | P(S)=0.90, incorrect                     | Posterior decrease minimal            | ✅     |

### 1.3 Learning Transition

| ID      | Test Case           | Input                   | Expected             | Status |
| ------- | ------------------- | ----------------------- | -------------------- | ------ |
| BKT-T01 | Standard transition | posterior=0.3, P(T)=0.2 | 0.3 + 0.7×0.2 = 0.44 | ✅     |
| BKT-T02 | Already mastered    | posterior=1.0, P(T)=0.2 | 1.0 (no change)      | ✅     |
| BKT-T03 | Zero learn rate     | posterior=0.3, P(T)=0.0 | 0.3 (no transition)  | ✅     |
| BKT-T04 | Never decreases     | any posterior, any P(T) | result ≥ posterior   | ✅     |

### 1.4 Full Update Cycle

| ID      | Test Case                 | Input               | Expected                                  | Status |
| ------- | ------------------------- | ------------------- | ----------------------------------------- | ------ |
| BKT-F01 | Correct increases mastery | state(0.1), correct | p_after > 0.1                             | ✅     |
| BKT-F02 | 3 correct in sequence     | 3× correct          | Strictly increasing                       | ✅     |
| BKT-F03 | 3 incorrect in sequence   | 3× incorrect        | 0 ≤ mastery ≤ 1                           | ✅     |
| BKT-F04 | 50 correct → near 1.0     | 50× correct         | mastery > 0.99                            | ✅     |
| BKT-F05 | 100 correct → converges   | 100× correct        | mastery > 0.999                           | ✅     |
| BKT-F06 | 100 incorrect bounded     | 100× incorrect      | 0 ≤ mastery ≤ 1                           | ✅     |
| BKT-F07 | Alternating C/I           | 100× alternating    | Moderate mastery (> 0.3)                  | ✅     |
| BKT-F08 | State mutated in-place    | any update          | state.p_learned == result.p_learned_after | ✅     |
| BKT-F09 | update_count increments   | any update          | state.update_count += 1                   | ✅     |

### 1.5 Mathematical Invariants

| ID      | Test Case                                                      | Expected                             | Status |
| ------- | -------------------------------------------------------------- | ------------------------------------ | ------ |
| BKT-M01 | P(L\|correct) ≥ P(L\|incorrect)                                | Always true for any prior            | ✅     |
| BKT-M02 | Posterior ∈ [0, 1]                                             | All combinations of P(L), P(S), P(G) | ✅     |
| BKT-M03 | Symmetry: P(G)=P(S) → correct pushes up, incorrect pushes down | P(L)=0.5, P(G)=P(S)=0.2              | ✅     |

---

## 2. Test Cases — Adaptive Difficulty

Implementation: `backend/app/engine/content_selector.py`  
Test files: `backend/app/engine/test_content_selector.py` (27 tests) + `tests/test_bkt_extended.py`

### 2.1 Difficulty Mapping

| ID    | Mastery   | Expected Tier | Rationale                    | Status |
| ----- | --------- | ------------- | ---------------------------- | ------ |
| AD-01 | 0.0       | low           | Below 0.4 threshold          | ✅     |
| AD-02 | 0.39      | low           | Just below boundary          | ✅     |
| AD-03 | 0.3999999 | low           | Floating-point edge          | ✅     |
| AD-04 | 0.4       | mid           | Exactly at low→mid boundary  | ✅     |
| AD-05 | 0.4000001 | mid           | Just above boundary          | ✅     |
| AD-06 | 0.5       | mid           | Clear mid-range              | ✅     |
| AD-07 | 0.69      | mid           | Just below mid→high boundary | ✅     |
| AD-08 | 0.6999999 | mid           | Floating-point edge          | ✅     |
| AD-09 | 0.7       | high          | Exactly at mid→high boundary | ✅     |
| AD-10 | 0.7000001 | high          | Just above boundary          | ✅     |
| AD-11 | 1.0       | high          | Maximum mastery              | ✅     |
| AD-12 | -0.1      | low           | Defensive: negative mastery  | ✅     |
| AD-13 | 1.5       | high          | Defensive: mastery > 1       | ✅     |

### 2.2 Content Selection Pipeline

| ID    | Test Case                    | Expected                                             | Status |
| ----- | ---------------------------- | ---------------------------------------------------- | ------ |
| CS-01 | Correct skill filtering      | Selected item matches requested skill                | ✅     |
| CS-02 | Correct tier at low mastery  | tier_used == "low" when mastery=0.2                  | ✅     |
| CS-03 | Correct tier at mid mastery  | tier_used == "mid" when mastery=0.5                  | ✅     |
| CS-04 | Correct tier at high mastery | tier_used == "high" when mastery=0.8                 | ✅     |
| CS-05 | Repetition exclusion         | Item in recent_ids never returned                    | ✅     |
| CS-06 | No immediate repeat          | 10 sequential picks → no two consecutive same        | ✅     |
| CS-07 | History trimmed              | History never exceeds DEFAULT_HISTORY_SIZE (5)       | ✅     |
| CS-08 | Tier fallback (no items)     | Catalog only has low → mid request falls back to low | ✅     |
| CS-09 | History exhaustion reset     | All items blocked → history clears and retries       | ✅     |
| CS-10 | Higher weight favored        | weight=2.0 item picked ~2× more than weight=1.0      | ✅     |
| CS-11 | Zero-weight uniform fallback | All weights 0 → uniform random selection             | ✅     |
| CS-12 | Single-item pool             | Deterministic pick, pool_size=1                      | ✅     |

### 2.3 Integration: BKT → Difficulty → Selection

| ID     | Test Case                            | Expected                                           | Status |
| ------ | ------------------------------------ | -------------------------------------------------- | ------ |
| INT-01 | New student gets easy items          | mastery=0.1 → low-tier item                        | ✅     |
| INT-02 | Mastery progression changes tier     | Correct answers → low → mid → high over time       | ✅     |
| INT-03 | Tier matches selected item           | select_difficulty(mastery) == item.difficulty      | ✅     |
| INT-04 | select_difficulty aliases consistent | select_difficulty ≡ select_difficulty_from_mastery | ✅     |

---

## 3. Test Cases — API Endpoints

Implementation: `backend/app/api/routes.py`  
Test file: `tests/test_api_endpoints.py`

### 3.1 POST /api/sessions

| ID      | Test Case                | Method/Body                 | Expected Code | Expected Body                      |
| ------- | ------------------------ | --------------------------- | ------------- | ---------------------------------- |
| API-S01 | Create session — valid   | `{"display_name": "Alice"}` | 200           | ok=true, session_id present        |
| API-S02 | Empty name               | `{"display_name": ""}`      | 422           | Validation error                   |
| API-S03 | Name too long (>64)      | `{"display_name": "x"*65}`  | 422           | Validation error                   |
| API-S04 | Missing body             | (none)                      | 422           | Body required                      |
| API-S05 | Envelope shape           | valid                       | 200           | ok, data, error, meta all present  |
| API-S06 | Meta contains session_id | valid                       | 200           | meta.session_id == data.session_id |
| API-S07 | Mastery initial values   | valid                       | 200           | All skills ∈ [0, 1]                |

### 3.2 GET /api/sessions/{id}/mastery

| ID      | Test Case               | URL                      | Expected Code | Notes                              |
| ------- | ----------------------- | ------------------------ | ------------- | ---------------------------------- |
| API-M01 | Valid session           | `/{valid_id}/mastery`    | 200           | 3 skills returned                  |
| API-M02 | Nonexistent session     | `/{random_uuid}/mastery` | 404           | SESSION_NOT_FOUND                  |
| API-M03 | Malformed UUID          | `/not-a-uuid/mastery`    | 422           | Validation error                   |
| API-M04 | Summary matches details | valid                    | 200           | summary[skill] == detail.p_learned |
| API-M05 | Difficulty tier valid   | valid                    | 200           | tier ∈ {low, mid, high}            |

### 3.3 GET /api/sessions/{id}/next-item

| ID      | Test Case                | Query Param                          | Expected Code | Notes                  |
| ------- | ------------------------ | ------------------------------------ | ------------- | ---------------------- |
| API-N01 | Valid vocabulary request | `?skill=vocabulary`                  | 200           | Returns puzzle variant |
| API-N02 | Valid grammar request    | `?skill=grammar`                     | 200           | skill == "grammar"     |
| API-N03 | Valid listening request  | `?skill=listening`                   | 200           | skill == "listening"   |
| API-N04 | Invalid skill            | `?skill=algebra`                     | 422           | Pattern validation     |
| API-N05 | Missing skill param      | (none)                               | 422           | Required query         |
| API-N06 | Nonexistent session      | `/{fake}/next-item?skill=vocabulary` | 404           | SESSION_NOT_FOUND      |
| API-N07 | Response has prompt_text | valid                                | 200           | Non-empty string       |
| API-N08 | Response has variant_id  | valid                                | 200           | Non-empty string       |

### 3.4 POST /api/sessions/{id}/attempts

| ID      | Test Case                         | Body                           | Expected Code | Notes                          |
| ------- | --------------------------------- | ------------------------------ | ------------- | ------------------------------ |
| API-A01 | Valid submission                  | Full body with real variant_id | 200           | Feedback returned              |
| API-A02 | Missing variant_id                | Omit variant_id                | 422           | Required field                 |
| API-A03 | Empty answer                      | `"answer": ""`                 | 422           | min_length=1                   |
| API-A04 | Negative response_time            | `"response_time_ms": -100`     | 422           | ge=0 constraint                |
| API-A05 | Nonexistent variant               | `"variant_id": "ghost"`        | 400           | ATTEMPT_ERROR                  |
| API-A06 | Mastery updates after submit      | Submit → GET mastery           | 200           | update_count ≥ 1               |
| API-A07 | Feedback contains correct_answers | valid                          | 200           | list of strings                |
| API-A08 | Feedback has before/after mastery | valid                          | 200           | p_learned_before/after present |
| API-A09 | Nonexistent session               | `/{fake_id}/attempts`          | 404           | SESSION_NOT_FOUND              |

### 3.5 GET /health

| ID      | Test Case       | Expected |
| ------- | --------------- | -------- |
| API-H01 | Health endpoint | 200 OK   |

---

## 4. Test Cases — Glitch Rendering

Implementation: `frontend/src/components/GlitchText.tsx`  
Test file: `frontend/src/components/__tests__/GlitchText.test.tsx`

### 4.1 Core Formula: `glitch_level = 1 − mastery`

| ID    | Mastery In | glitch_level | --glitch Out | --glitch-px Out | Notes                |
| ----- | ---------- | ------------ | ------------ | --------------- | -------------------- |
| GL-01 | 0.0        | 1.0          | 1            | 8px             | Maximum glitch       |
| GL-02 | 0.1        | 0.9          | 0.9          | 7px             | Heavy glitch         |
| GL-03 | 0.5        | 0.5          | 0.5          | 4px             | Moderate glitch      |
| GL-04 | 0.9        | 0.1          | 0.1          | 1px             | Mild glitch          |
| GL-05 | 0.95       | 0.05         | 0            | 0px             | Threshold → killed   |
| GL-06 | 0.96       | 0.04         | 0            | 0px             | Below threshold      |
| GL-07 | 1.0        | 0.0          | 0            | 0px             | No glitch (mastered) |

### 4.2 Boundary & Clamping

| ID    | Mastery In | Expected --glitch      | Rationale                         |
| ----- | ---------- | ---------------------- | --------------------------------- |
| GL-08 | -0.5       | 1                      | Clamped: max(0, min(1, 1.5)) = 1  |
| GL-09 | 1.5        | 0                      | Clamped: max(0, min(1, -0.5)) = 0 |
| GL-10 | NaN        | Test: should not crash | Defensive                         |

### 4.3 DOM Output

| ID    | Test Case                       | Expected                              |
| ----- | ------------------------------- | ------------------------------------- |
| GL-11 | Default tag is `<span>`         | tagName == "SPAN"                     |
| GL-12 | as="h1" renders `<h1>`          | tagName == "H1"                       |
| GL-13 | as="p" renders `<p>`            | tagName == "P"                        |
| GL-14 | data-text matches children      | getAttribute("data-text") == children |
| GL-15 | CSS class "glitch-text" applied | classList contains "glitch-text"      |
| GL-16 | Additional className merged     | className contains custom classes     |

### 4.4 CSS Animation Tiers (Visual QA — Manual)

| Mastery | Visual Expectation                                                 |
| ------- | ------------------------------------------------------------------ |
| 0.0–0.2 | Heavy chromatic aberration, 6-8px displacement, clearly unreadable |
| 0.3–0.5 | Moderate flicker, 3-4px displacement, readable with effort         |
| 0.6–0.8 | Mild occasional twitch, 1-2px displacement, easily readable        |
| 0.9–1.0 | No visible effect, completely clean text                           |

---

## 5. Edge Case Scenarios

### 5.1 BKT Engine Edge Cases

| #   | Scenario                                       | Input                                    | Expected Behavior                          | Risk       |
| --- | ---------------------------------------------- | ---------------------------------------- | ------------------------------------------ | ---------- |
| E01 | **Division by zero** — P(L)=0, P(G)=0, correct | denominator = 0                          | Returns p_learned unchanged (guard clause) | Medium     |
| E02 | **All params = 0**                             | p_init=0, p_learn=0, p_guess=0, p_slip=0 | No crash; mastery stays 0                  | Medium     |
| E03 | **All params = 1**                             | p_init=1, p_learn=1, p_guess=1, p_slip=1 | No crash; mastery stays 1                  | Medium     |
| E04 | **Rapid-fire 1000 updates**                    | 1000 sequential corrects                 | mastery ≈ 1.0, no overflow                 | Low        |
| E05 | **Float precision drift**                      | Alternating C/I for 10000 rounds         | mastery ∈ [0, 1], no NaN/Inf               | Low        |
| E06 | **Negative parameter**                         | p_init = -0.01                           | ValueError from SkillParams validation     | Handled ✅ |
| E07 | **Parameter > 1**                              | p_slip = 1.1                             | ValueError from SkillParams validation     | Handled ✅ |

### 5.2 Content Selector Edge Cases

| #   | Scenario                          | Expected Behavior                        | Risk       |
| --- | --------------------------------- | ---------------------------------------- | ---------- |
| E08 | **Empty catalog**                 | ValueError raised                        | Handled ✅ |
| E09 | **No items for requested skill**  | ValueError raised                        | Handled ✅ |
| E10 | **All items in recent_ids**       | History auto-clears, retry succeeds      | Handled ✅ |
| E11 | **Single item in entire catalog** | Returns that item deterministically      | Handled ✅ |
| E12 | **All zero-weight items**         | Uniform random fallback                  | Handled ✅ |
| E13 | **History size = 0**              | No repetition prevention; works normally | Low        |
| E14 | **Skill name case sensitivity**   | "Vocabulary" vs "vocabulary" → no match  | Medium     |

### 5.3 API Edge Cases

| #   | Scenario                                | Expected Behavior                                            | Risk                 |
| --- | --------------------------------------- | ------------------------------------------------------------ | -------------------- |
| E15 | **Concurrent session creation**         | Each gets unique session_id                                  | Low (UUID4)          |
| E16 | **Submit to expired/deleted session**   | 404 SESSION_NOT_FOUND                                        | Medium               |
| E17 | **Submit same variant_id twice**        | Both recorded; attempt_number increments                     | Handled ✅           |
| E18 | **Submit with response_time_ms = 0**    | Accepted (ge=0 constraint)                                   | Handled ✅           |
| E19 | **Submit with huge response_time**      | response_time_ms = 2^31-1                                    | Accepted (int field) |
| E20 | **Unicode in display_name**             | `"名前"` → should work fine                                  | Low                  |
| E21 | **Unicode in answer**                   | `"café"` → case-insensitive comparison                       | Medium               |
| E22 | **SQL injection in answer**             | `"'; DROP TABLE--"` → parameterized query, safe              | Handled ✅           |
| E23 | **XSS in display_name**                 | `"<script>alert(1)</script>"` → stored as text, no rendering | Low                  |
| E24 | **Concurrent BKT updates same session** | Race condition on p_ln update                                | **High** ⚠️          |

### 5.4 Frontend Edge Cases

| #   | Scenario                         | Expected Behavior                                     | Risk       |
| --- | -------------------------------- | ----------------------------------------------------- | ---------- |
| E25 | **API server down**              | Error state shown, "CONNECTING…" doesn't hang forever | Medium     |
| E26 | **Slow network (>5s response)**  | Loading indicator stays visible                       | Low        |
| E27 | **Empty prompt_text from API**   | Blank puzzle area, no crash                           | Medium     |
| E28 | **Audio URL 404**                | Howler fails silently, puzzle still functional        | Low        |
| E29 | **Browser back button mid-game** | State preserved in Zustand (in-memory)                | Low        |
| E30 | **Double-click submit**          | Loading flag prevents duplicate submission            | Handled ✅ |
| E31 | **Very long answer text**        | Input accepts; server validates                       | Low        |

---

## 6. Example API Test Calls

### 6.1 Create Session

```bash
# ── Request ──
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"display_name": "QA_Tester_01"}'

# ── Expected Response (200) ──
{
  "ok": true,
  "data": {
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890",
    "player_id": "f9e8d7c6-b5a4-3210-fedc-ba0987654321",
    "session_token": "tok_abc123",
    "mastery": {
      "vocabulary": 0.1,
      "grammar": 0.1,
      "listening": 0.1
    },
    "current_room": "room_1"
  },
  "error": null,
  "meta": {
    "timestamp": "2026-03-01T12:00:00Z",
    "session_id": "a1b2c3d4-e5f6-7890-abcd-ef1234567890"
  }
}
```

### 6.2 Get Mastery

```bash
# ── Request ──
curl http://localhost:8000/api/sessions/{session_id}/mastery

# ── Expected Response (200) ──
{
  "ok": true,
  "data": {
    "session_id": "a1b2c3d4-...",
    "mastery": [
      {"skill": "vocabulary", "p_learned": 0.1, "update_count": 0, "difficulty_tier": "low"},
      {"skill": "grammar",    "p_learned": 0.1, "update_count": 0, "difficulty_tier": "low"},
      {"skill": "listening",  "p_learned": 0.1, "update_count": 0, "difficulty_tier": "low"}
    ],
    "summary": {"vocabulary": 0.1, "grammar": 0.1, "listening": 0.1}
  },
  "error": null,
  "meta": {"timestamp": "2026-03-01T12:00:01Z", "session_id": "a1b2c3d4-..."}
}
```

### 6.3 Get Next Item

```bash
# ── Request ──
curl "http://localhost:8000/api/sessions/{session_id}/next-item?skill=vocabulary"

# ── Expected Response (200) ──
{
  "ok": true,
  "data": {
    "puzzle_id": "room1_vocab_decode",
    "variant_id": "room1_vocab_decode__low_1",
    "skill": "vocabulary",
    "difficulty_tier": "low",
    "prompt_text": "Translate: 'Where is the signal tower?'",
    "audio_url": null,
    "time_limit_sec": 60,
    "fallback_used": false
  },
  "error": null,
  "meta": {"timestamp": "...", "session_id": "..."}
}
```

### 6.4 Submit Attempt — Correct Answer

```bash
# ── Request ──
curl -X POST http://localhost:8000/api/sessions/{session_id}/attempts \
  -H "Content-Type: application/json" \
  -d '{
    "variant_id": "room1_vocab_decode__low_1",
    "answer": "radio tower",
    "response_time_ms": 4200,
    "hint_count_used": 0
  }'

# ── Expected Response (200) ──
{
  "ok": true,
  "data": {
    "is_correct": true,
    "correct_answers": ["radio tower", "signal tower"],
    "p_learned_before": 0.1,
    "p_learned_after": 0.4286,
    "difficulty_tier": "mid",
    "mastery": {
      "vocabulary": 0.4286,
      "grammar": 0.1,
      "listening": 0.1
    }
  },
  "error": null,
  "meta": {"timestamp": "...", "session_id": "..."}
}
```

### 6.5 Submit Attempt — Wrong Answer

```bash
curl -X POST http://localhost:8000/api/sessions/{session_id}/attempts \
  -H "Content-Type: application/json" \
  -d '{
    "variant_id": "room1_vocab_decode__low_1",
    "answer": "wrong answer",
    "response_time_ms": 8500,
    "hint_count_used": 1
  }'

# ── Expected Response (200) ──
{
  "ok": true,
  "data": {
    "is_correct": false,
    "correct_answers": ["radio tower", "signal tower"],
    "p_learned_before": 0.1,
    "p_learned_after": 0.2117,
    "difficulty_tier": "low",
    "mastery": {
      "vocabulary": 0.2117,
      "grammar": 0.1,
      "listening": 0.1
    }
  },
  "error": null,
  "meta": {"timestamp": "...", "session_id": "..."}
}
```

### 6.6 Error Responses

```bash
# ── 404: Session not found ──
curl http://localhost:8000/api/sessions/00000000-0000-0000-0000-000000000000/mastery
# → HTTP 404
# {"detail": {"ok": false, "error": {"code": "SESSION_NOT_FOUND", "message": "..."}, ...}}

# ── 422: Invalid skill parameter ──
curl "http://localhost:8000/api/sessions/{id}/next-item?skill=math"
# → HTTP 422
# {"detail": [{"msg": "String should match pattern...", ...}]}

# ── 422: Empty display_name ──
curl -X POST http://localhost:8000/api/sessions \
  -H "Content-Type: application/json" \
  -d '{"display_name": ""}'
# → HTTP 422

# ── 400: Nonexistent variant_id ──
curl -X POST http://localhost:8000/api/sessions/{id}/attempts \
  -H "Content-Type: application/json" \
  -d '{"variant_id": "ghost", "answer": "x", "response_time_ms": 100, "hint_count_used": 0}'
# → HTTP 400
# {"detail": {"ok": false, "error": {"code": "ATTEMPT_ERROR", "message": "Variant ghost not found"}}}
```

### 6.7 Full Gameplay Sequence (E2E Smoke Test)

```bash
#!/bin/bash
# End-to-end smoke test: create session → solve vocabulary → check mastery

BASE="http://localhost:8000"

# Step 1: Create session
SESSION=$(curl -s -X POST "$BASE/api/sessions" \
  -H "Content-Type: application/json" \
  -d '{"display_name": "E2E_Smoke"}' | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['session_id'])")
echo "Session: $SESSION"

# Step 2: Get vocabulary puzzle
ITEM=$(curl -s "$BASE/api/sessions/$SESSION/next-item?skill=vocabulary")
VARIANT_ID=$(echo "$ITEM" | python3 -c "import sys,json; print(json.load(sys.stdin)['data']['variant_id'])")
echo "Variant: $VARIANT_ID"

# Step 3: Submit an answer
FEEDBACK=$(curl -s -X POST "$BASE/api/sessions/$SESSION/attempts" \
  -H "Content-Type: application/json" \
  -d "{\"variant_id\": \"$VARIANT_ID\", \"answer\": \"test\", \"response_time_ms\": 3000, \"hint_count_used\": 0}")
echo "Feedback: $FEEDBACK"

# Step 4: Verify mastery updated
MASTERY=$(curl -s "$BASE/api/sessions/$SESSION/mastery")
echo "Mastery: $MASTERY"
```

---

## 7. Failure Handling Strategies

### 7.1 Backend Failure Handling

| Layer                | Failure Mode                  | Strategy                                                     | Implementation                                    |
| -------------------- | ----------------------------- | ------------------------------------------------------------ | ------------------------------------------------- |
| **BKT Engine**       | Division by zero in posterior | Guard clause: return current `p_learned` unchanged           | `_posterior_correct()` / `_posterior_incorrect()` |
| **BKT Engine**       | Invalid parameters (neg / >1) | Fail-fast: `SkillParams.__post_init__()` raises `ValueError` | Validated at construction                         |
| **Content Selector** | Empty catalog for skill       | Raise `ValueError` with descriptive message                  | `select_item()` line ~135                         |
| **Content Selector** | All items blocked by history  | Auto-clear history and retry (max 1 recursion)               | `select_item()` step 5                            |
| **Content Selector** | Zero-weight items             | Fallback to uniform random                                   | `_weighted_choice()` guard                        |
| **API Layer**        | Session not found             | HTTPException 404 with `SESSION_NOT_FOUND` code              | Every route checks session                        |
| **API Layer**        | Variant not found             | HTTPException 400 with `ATTEMPT_ERROR` code                  | `submit_attempt()`                                |
| **API Layer**        | Validation failure            | FastAPI auto-returns 422 with field details                  | Pydantic schemas                                  |
| **Database**         | Connection failure            | SQLAlchemy raises, FastAPI returns 500                       | Unhandled (needs middleware)                      |
| **Database**         | Constraint violation          | IntegrityError → should return 409/400                       | **Not yet handled** ⚠️                            |

### 7.2 Frontend Failure Handling

| Component             | Failure Mode            | Strategy                                                       | Implementation                         |
| --------------------- | ----------------------- | -------------------------------------------------------------- | -------------------------------------- |
| **API Client**        | Non-2xx response        | Parse envelope if available; fallback generic error            | `request<T>()` in `api.ts`             |
| **API Client**        | Network timeout/offline | Catch fetch error → `{ok: false, error: {code: "HTTP_ERROR"}}` | `request<T>()`                         |
| **Zustand Store**     | API returns error       | Set `error` state, clear `loading`                             | Every async action                     |
| **Game Page**         | Error state             | Red error text shown below form                                | `{error && <p>…</p>}`                  |
| **Game Page**         | Loading state           | Disabled buttons + "…" text                                    | `disabled={loading}`                   |
| **Game Page**         | Double-click prevention | `loading` flag disables submit                                 | `disabled={loading}`                   |
| **GlitchText**        | Out-of-range mastery    | Clamped: `Math.max(0, Math.min(1, 1 - mastery))`               | `GlitchText.tsx`                       |
| **Audio**             | File 404 / decode error | Howler.js fails silently; no crash                             | `useAudio.ts`                          |
| **Audio**             | Browser autoplay policy | Ambient starts on user-initiated click (form submit)           | `startAmbient()` called on form submit |
| **Phase Progression** | Missing currentItem     | Phase components return `null`                                 | `if (!currentItem) return null`        |

### 7.3 Recommended Additions (Not Yet Implemented)

| Priority | Recommendation                                      | Rationale                                               |
| -------- | --------------------------------------------------- | ------------------------------------------------------- |
| **P0**   | Add global error-handling middleware in FastAPI     | Unhandled DB errors currently return raw 500            |
| **P0**   | Add retry logic with backoff in frontend API client | Network glitches shouldn't crash the game               |
| **P1**   | Add optimistic locking on `skill_estimates`         | Prevents race condition (E24) on concurrent BKT updates |
| **P1**   | Add request timeout (10s) in frontend fetch         | Prevents infinite loading states                        |
| **P2**   | Add circuit breaker pattern for DB connection       | Graceful degradation under DB outages                   |
| **P2**   | Add frontend error boundary (React)                 | Catch rendering errors without white-screen             |
| **P3**   | Add structured logging for all API errors           | Observability and debugging in production               |
| **P3**   | Add rate limiting on POST endpoints                 | Prevent abuse / accidental spam                         |

### 7.4 Failure Recovery Matrix

```
┌─────────────────────┬──────────────────┬───────────────────┬──────────────┐
│ Failure             │ Detection        │ Recovery          │ User Impact  │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ DB connection lost  │ SQLAlchemy error  │ Retry 3x, then   │ "Server      │
│                     │ in get_db()       │ show maintenance  │ unavailable" │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ BKT NaN/Inf         │ isnan() check    │ Reset to p_init   │ Invisible to │
│                     │ after update      │                   │ player       │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ Empty puzzle pool   │ ValueError from   │ Return 400 with   │ "No puzzles  │
│                     │ selector          │ clear message     │ available"   │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ Session expired     │ 404 from API      │ Frontend calls    │ "Session     │
│                     │                   │ reset(), show     │ expired,     │
│                     │                   │ lobby screen      │ start new"   │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ Audio load failure  │ Howler error evt  │ Continue without  │ No audio,    │
│                     │                   │ audio; text-only  │ game works   │
├─────────────────────┼──────────────────┼───────────────────┼──────────────┤
│ Concurrent submit   │ Loading flag      │ Ignore 2nd click  │ None         │
│ (double-click)      │                   │                   │              │
└─────────────────────┴──────────────────┴───────────────────┴──────────────┘
```

---

## Test Execution Summary

| Suite                     | File                                                    | Test Count | Framework              |
| ------------------------- | ------------------------------------------------------- | ---------- | ---------------------- |
| BKT Unit Tests            | `backend/app/engine/test_bkt.py`                        | 32         | pytest                 |
| Content Selector Tests    | `backend/app/engine/test_content_selector.py`           | 27         | pytest                 |
| BKT Extended + Difficulty | `tests/test_bkt_extended.py`                            | 24         | pytest                 |
| API Integration Tests     | `tests/test_api_endpoints.py`                           | ~22        | pytest-asyncio + httpx |
| Glitch Rendering Tests    | `frontend/src/components/__tests__/GlitchText.test.tsx` | ~20        | Jest/Vitest + RTL      |
| **Total**                 |                                                         | **~125**   |                        |

```bash
# Run all backend tests
python -m pytest tests/ backend/app/engine/ -v

# Run frontend tests
cd frontend && npx vitest run
```

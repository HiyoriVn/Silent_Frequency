<!-- CHANGELOG: updated 2026-03-21: normalized to English and expanded gameplay v2 implementation constraints, typed payloads, and rollback guidance -->

# AGENTS.md

## 1. Project Overview

- Silent Frequency is an adaptive language-learning escape-room game.
- Backend owns session progression, puzzle selection, scoring, and BKT mastery updates.
- Frontend renders session states and submits player actions through the API.

## 2. Tech Stack

- Backend: Python, FastAPI, SQLAlchemy async ORM, Pydantic v2, asyncpg.
- Database model targets PostgreSQL types (UUID, JSONB).
- Frontend: Next.js (App Router), React, TypeScript, Zustand, Howler.
- Styling: Tailwind CSS v4.
- Testing: pytest + pytest-asyncio (backend), Testing Library + Jest DOM (frontend component tests).
- Linting: ESLint (Next.js core-web-vitals + TypeScript config).

## 3. Project Structure

- `backend/app/main.py`: FastAPI app setup, lifespan, CORS, route registration.
- `backend/app/api/`: Pydantic API schemas and thin route handlers.
- `backend/app/services/`: Session, mastery, and puzzle business logic.
- `backend/app/engine/`: BKT math and content-selection engine.
- `backend/app/db/`: Async DB session setup and SQLAlchemy models.
- `backend/app/seed.py`: Seed data and seeding entrypoint.
- `frontend/src/app/page.tsx`: Main client flow (lobby, active puzzle, completion).
- `frontend/src/stores/gameStore.ts`: Single Zustand game/session state store.
- `frontend/src/lib/api.ts`: Thin fetch wrappers for backend endpoints.
- `frontend/src/lib/types.ts`: API envelope and shared domain types.
- `frontend/src/components/phases/`: Skill-specific puzzle UIs.
- `tests/`: API integration and extended BKT tests.
- `docs/session_flow.md`: Current backend-owned session-flow contract.

## 4. Development Commands

- Backend dependencies: `pip install -r backend/requirements.txt`
- Run backend API: `uvicorn backend.app.main:app --reload`
- Seed database: `python -m backend.app.seed`
- Backend unit tests:
  - `python -m pytest backend/app/engine/test_bkt.py -v`
  - `python -m pytest backend/app/engine/test_content_selector.py -v`
- Backend integration/extended tests:
  - `python -m pytest tests/test_api_endpoints.py -v`
  - `python -m pytest tests/test_bkt_extended.py -v`
- Frontend dependencies: `cd frontend && npm install`
- Run frontend dev server: `cd frontend && npm run dev`
- Frontend build/start: `cd frontend && npm run build` then `cd frontend && npm run start`
- Frontend lint: `cd frontend && npm run lint`

## 5. Coding Conventions

- Keep backend routes thin: validate input, delegate to `services`, return API envelope.
- Keep domain logic in `services` and `engine`, not in route handlers.
- Use type hints throughout backend code and typed interfaces in frontend TypeScript.
- Preserve API envelope shape in frontend and backend: `ok`, `data`, `error`, `meta`.
- Use snake_case for backend fields and request payloads; frontend mirrors API names where required (`session_id`, `variant_id`, etc.).
- Frontend imports use `@/*` path alias.
- Store server-derived game state in Zustand as the client mirror (server is source of truth).
- Follow existing file style: module docstring header comments in Python, concise component/service headers in TS/TSX.

## 6. Rules & Constraints

> **Phase-3 canonical:** The rules in this section are the default contract for current production flow.

- MUST keep session progression backend-owned (`current_level_index` flow from backend).
- MUST keep adaptive/static condition behavior in backend policy code.
- MUST keep BKT update logic in `backend/app/engine` and call it from services (do not reimplement in UI).
- MUST preserve SQLAlchemy model compatibility with current schema unless explicitly migrating.
- MUST update frontend `lib/types.ts` and API client when backend response contracts change.
- MUST NOT move progression decisions into frontend phase components/store.
- MUST NOT bypass service layer by putting business logic directly in routes.
- MUST NOT introduce new architectural patterns when existing service/store patterns already fit.

## 6.1 Game-mode v2 — Extension Rules (experimental — gameplay v2)

> **experimental — gameplay v2:** Additive rules for room/object/inventory actions. Do not replace Phase-3 canonical flow by default.

### Summary

- Gameplay v2 enables true escape-room interactions while keeping learning validity and backend authority.
- Every gameplay contract change MUST be versioned using `interaction_schema_version`.

### Mode and Feature-Flag Enforcement

- Session mode is immutable for an experiment run: `session.mode` is set at session creation and MUST NOT be changed mid-session.
- Server must enforce mode on each v2 endpoint: reject gameplay v2 calls when `session.mode != gameplay_v2`.
- Gameplay v2 must also be gated by a global feature flag (for example `GAMEPLAY_V2_ENABLED=true|false`).
- If the global flag is off, server should gracefully degrade to canonical Phase-3 flow and return a clear error envelope for blocked v2 endpoints.
- Example mode-gate failure: `403` with `error.code="MODE_MISMATCH"`.

### Typed Action Payload Requirement

- Requests to `POST /api/sessions/{session_id}/action` MUST be strongly typed and schema-validated.
- Minimum required fields: `interaction_schema_version`, `action`, `target_id`.
- Optional fields: `item_id`, `client_action_id`, `client_ts`.

```json
{
  "interaction_schema_version": 2,
  "action": "use_item",
  "target_id": "old_radio",
  "item_id": "bent_key",
  "client_action_id": "95d5e047-f9f2-4d8f-a05b-fd2a58f8f2bf"
}
```

### Declarative Effects Requirement

- Backend MUST return declarative `effects[]` only.
- Backend MUST NOT send executable scripts for client-side evaluation.

```json
{
  "ok": true,
  "data": {
    "effects": [
      { "type": "unlock", "target_id": "old_radio" },
      { "type": "show_dialogue", "dialogue_id": "radio_boot" },
      { "type": "open_puzzle", "puzzle_id": "listening_radio_01" }
    ]
  },
  "error": null,
  "meta": { "interaction_schema_version": 2 }
}
```

- Effects must be declarative state-change instructions only (no executable code, no dynamic script expressions).

### Telemetry Requirement

- Every resolved action MUST emit a `game_action` telemetry event.
- Required fields:
  - `session_id`
  - `action`
  - `target_id`
  - `item_id` (nullable)
  - `timestamp`
  - `resulting_effects[]`
- Optional field:
  - `client_action_id`

### Testing Requirement

- MUST add backend unit tests for action validation, resolver behavior, and effects mapping.
- MUST run an integration spike (session create -> action -> canonical state update -> `game_action` telemetry) before enabling v2 in shared environments.
- SHOULD preserve coexistence with `POST /api/sessions/{session_id}/attempts` for learning puzzle scoring.

### Error Handling Suggestion

- Use the standard envelope for failures:

```json
{
  "ok": false,
  "data": null,
  "error": {
    "code": "INVALID_ACTION",
    "message": "Unsupported action for target_id=old_radio."
  },
  "meta": { "interaction_schema_version": 2 }
}
```

- Recommended HTTP mapping:
  - `400` invalid payload / unsupported action / schema mismatch.
  - `403` authenticated but not allowed to mutate this session.
  - `404` session or target object not found.
  - `409` action conflict or stale state.
  - `500` unexpected server error.

### Admin and Rollback Guidance

- Provide an admin control to disable gameplay v2 globally by setting `GAMEPLAY_V2_ENABLED=false`.
- Rollback plan for pilot incidents: keep canonical Phase-3 endpoints active, disable v2 action routes via flag, and continue sessions in Phase-3 flow without schema or migration rollback.

## 7. Testing Guidelines

- Run relevant pytest suites for backend changes before completing work.
- Run `cd frontend && npm run lint` for frontend changes.
- Run targeted frontend component tests when touching component behavior.
- For API contract changes, verify both backend tests and frontend type/client alignment.
- Keep test fixtures seeded consistently with `backend/app/seed.py` data assumptions.

## 8. Agent Behavior Guidelines

- Prefer minimal, localized edits over broad refactors.
- Match existing layering: route -> service -> engine/db.
- Reuse existing types and helpers before adding new abstractions.
- When changing endpoints or payloads, update both sides in one task (backend schema/routes and frontend `lib/api.ts` + `lib/types.ts`).
- Preserve current naming and flow conventions unless explicitly instructed otherwise.
- If you detect mismatch between docs/tests and current routes, align tests/docs to implemented API instead of adding compatibility hacks.

## 9. Recent Local Changes & Recommendations

- **Dev server CORS/dev-origin:** Added `allowedDevOrigins` to `frontend/next.config.ts` to permit developer origin(s) (for example `http://26.83.101.154`) when fetching `_next` dev assets during development. Restart the Next dev server after changing this.
- **HMR / WebSocket note:** If accessing the dev site from another machine, start Next with hostname `0.0.0.0` (or set `HOST=0.0.0.0`) so the HMR websocket can connect; ensure port 3000 is reachable through firewall.
- **Frontend tests:** Tests previously failed with `TypeError: Failed to fetch` because they attempted real network requests. Recommended fixes:
  - Prefer mocking `frontend/src/lib/api.ts` per-test with `jest.mock("src/lib/api")` to return deterministic envelopes.
  - Alternatively add a global `fetch` mock in a Jest setup file (for example `jest.setup.ts`) if many tests rely on fetch directly.
- **Developer workflow:** For small debugging changes, prefer localized edits (config or test mocks) and run targeted validation. Avoid broad refactors in hotfixes.

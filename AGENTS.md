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

- MUST keep session progression backend-owned (`current_level_index` flow from backend).
- MUST keep adaptive/static condition behavior in backend policy code.
- MUST keep BKT update logic in `backend/app/engine` and call it from services (do not reimplement in UI).
- MUST preserve SQLAlchemy model compatibility with current schema unless explicitly migrating.
- MUST update frontend `lib/types.ts` and API client when backend response contracts change.
- MUST NOT move progression decisions into frontend phase components/store.
- MUST NOT bypass service layer by putting business logic directly in routes.
- MUST NOT introduce new architectural patterns when existing service/store patterns already fit.

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

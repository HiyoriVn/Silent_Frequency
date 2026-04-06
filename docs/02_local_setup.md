# Local Setup

## Prerequisites

Required tools:

- Python 3.11+
- Node.js 20+
- npm
- PostgreSQL
- Docker and Docker Compose (recommended for local development)

## Backend Setup

From repository root:

```bash
pip install -r backend/requirements.txt
```

Optional backend configuration may be read from environment variables or `backend/app/config.py`.

Example local database URL:

```text
postgresql+asyncpg://postgres:postgres@localhost:5432/silent_frequency
```

## Start the Backend

```bash
uvicorn backend.app.main:app --reload
```

Default local API base:

```text
http://localhost:8000
```

## Seed Initial Data

```bash
python -m backend.app.seed
```

This should load baseline puzzle content and any current gameplay v2-compatible room content.

## Frontend Setup

```bash
cd frontend
npm install
npm run dev
```

Default frontend URL:

```text
http://localhost:3000
```

## Optional Docker Setup

If using Docker Compose:

```bash
docker compose up -d
```

Use this when you want a more reproducible local database or service environment.

## Quick Validation Checklist

After setup, verify:

1. backend `/health` returns `ok`
2. seed script completes successfully
3. frontend loads
4. frontend can create a session
5. frontend can fetch a puzzle
6. frontend can submit an attempt

## Common Problems

### Seed/content mismatch

If tests fail unexpectedly, inspect:

- `backend/app/seed.py`
- `backend/app/content/`
- backend service assumptions about content IDs

### Frontend fetch failures in tests

Prefer mocking the API client rather than relying on real network calls in component tests.

### Cross-device development issues

If accessing the frontend from another device:

- bind Next.js to `0.0.0.0`
- ensure the backend and frontend ports are reachable
- confirm HMR websocket access is not blocked

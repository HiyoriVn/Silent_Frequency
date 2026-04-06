# Local Setup and Testing

## Backend Setup

From workspace root:

1. Install backend dependencies:

```bash
pip install -r backend/requirements.txt
```

2. Start API server:

```bash
uvicorn backend.app.main:app --reload
```

3. Seed database content:

```bash
python -m backend.app.seed
```

## Frontend Setup

From workspace root:

1. Install frontend dependencies:

```bash
cd frontend
npm install
```

2. Run frontend dev server:

```bash
npm run dev
```

Frontend default URL is typically `http://localhost:3000`.

## Environment Configuration

### Backend

Optional `.env` values for backend:

- `DATABASE_URL` equivalent setting is read as `database_url` in `backend/app/config.py`
- default DB URL: `postgresql+asyncpg://postgres:postgres@localhost:5432/silent_frequency`

## Quick Validation Checklist

1. Backend `/health` returns `ok`.
2. Seed command prints inserted/updated summary.
3. Frontend loads and can create a session.
4. Frontend can fetch next puzzle and submit attempts.

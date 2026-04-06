# Operations Runbook (Batch 4.3)

## Gameplay v2 Feature Flag

Primary toggle: `GAMEPLAY_V2_ENABLED`.

Recommended defaults:

- staging: `GAMEPLAY_V2_ENABLED=true` for controlled pilot validation
- production: `GAMEPLAY_V2_ENABLED=false` by default until pilot approval

### Enable gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=true
uvicorn backend.app.main:app --reload
```

### Disable gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=false
uvicorn backend.app.main:app --reload
```

## Rollback Procedure (Pilot-safe)

1. Disable gameplay v2 globally: set `GAMEPLAY_V2_ENABLED=false`.
2. Stop creating new gameplay-v2 sessions:
   - force mode default to `phase3` for new session creation clients.
3. Let existing pilot sessions finish naturally where possible.
4. If immediate hard revert is required:
   - mark active gameplay-v2 sessions inactive via admin SQL/update process.
5. Keep canonical Phase-3 endpoints online throughout rollback.

## DB Backup and Migration

Use the script in [scripts/db_backup_and_migrate.sh](scripts/db_backup_and_migrate.sh).

### Backup first (required)

```bash
export DB_CONTAINER=<postgres_container>
export PGUSER=postgres
export PGDATABASE=silent_frequency
./scripts/db_backup_and_migrate.sh backup
```

### Apply migration (interactive confirmation required)

```bash
./scripts/db_backup_and_migrate.sh migrate
```

### Restore if needed

```bash
./scripts/db_backup_and_migrate.sh restore
```

## Post-migration Checklist

1. Run smoke tests for `GET /api/sessions/{id}/game-state` and `POST /api/sessions/{id}/action`.
2. Verify event log growth for `game_action`, `puzzle_interaction_trace`, and `attempt_submitted`.
3. Verify metrics counters:
   - `telemetry.game_action.count`
   - `telemetry.trace.truncated`
   - `telemetry.trace.too_large`
4. Confirm no regression in `POST /api/sessions/{id}/attempts` flow.
5. Confirm gameplay_v2 modal attempts include `metadata.source="gameplay_v2"` in attempt telemetry payload.

## action_dedupe Cleanup Job

Cleanup script: [backend/app/maintenance/cleanup_action_dedupe.py](backend/app/maintenance/cleanup_action_dedupe.py)

### Dry run

```bash
python -m backend.app.maintenance.cleanup_action_dedupe --days 30 --dry-run
```

### Execute cleanup

```bash
python -m backend.app.maintenance.cleanup_action_dedupe --days 30 --batch-size 500
```

Scheduling guidance:

- run via cron/systemd or a containerized scheduled job
- recommended cadence: daily
- keep retention aligned with dedupe retry horizon (default 30 days)

## Known Phase-3 Test Triage (Not a Fix)

Issue pattern: failures in `tests/test_api_endpoints.py` can occur from Phase-3 seed/content mismatch.

How to reproduce:

```bash
python -m pytest tests/test_api_endpoints.py -v
```

Where to inspect:

1. [backend/app/seed.py](backend/app/seed.py)
2. [backend/app/content](backend/app/content)
3. [backend/app/services/puzzle_service.py](backend/app/services/puzzle_service.py)
4. [backend/app/api/routes.py](backend/app/api/routes.py)

Common mismatch causes:

- expected route contract differs from implemented endpoint naming/shape
- seed content IDs no longer align with test fixtures
- level/slot assumptions in old tests diverge from current backend-owned flow

## Batch 4.5 Integration QA Commands

```bash
python -m pytest -q \
   backend/app/tests/test_attempt_from_gameplay_v2.py \
   backend/app/tests/test_hint_count_and_trace_backend.py \
   backend/app/tests/test_trace_trimming_metrics.py \
   backend/app/tests/test_game_action_telemetry_exists.py

cd frontend && npm run test -- \
   tests/PuzzleScreen.409.test.tsx \
   tests/HintPanel.test.tsx \
   tests/Trace.cap.test.tsx
```

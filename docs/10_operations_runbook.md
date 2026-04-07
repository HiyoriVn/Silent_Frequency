<!-- CHANGELOG: pass-2 canonical rewrite preserving feature-flag control, rollback, migration, cleanup, and QA commands -->

# Operations Runbook

## Scope

This runbook documents development and pilot-safe operational procedures for Silent Frequency.

It covers:

- gameplay v2 feature-flag control
- rollback
- migration and database safety
- post-change validation
- scheduled maintenance
- known test triage patterns

---

## 1. Gameplay v2 Feature Flag

Primary toggle:

```text
GAMEPLAY_V2_ENABLED
```

Recommended defaults:

- staging: `GAMEPLAY_V2_ENABLED=true` for controlled pilot validation
- production: `GAMEPLAY_V2_ENABLED=false` by default until pilot approval

### Enable Gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=true
uvicorn backend.app.main:app --reload
```

### Disable Gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=false
uvicorn backend.app.main:app --reload
```

---

## 2. Rollback Procedure (Pilot-safe)

If gameplay v2 causes instability:

1. disable gameplay v2 globally by setting `GAMEPLAY_V2_ENABLED=false`
2. stop creating new gameplay v2 sessions
   - force mode default to `phase3` for new session creation clients

3. let existing pilot sessions finish naturally where possible
4. if immediate hard revert is required:
   - mark active gameplay v2 sessions inactive through admin SQL or admin tooling

5. keep canonical Phase-3 endpoints online throughout rollback

### Rollback Rule

Do not invent new runtime behavior during incident response.

Prefer disabling the experimental path while preserving canonical Phase-3 operation.

---

## 3. Database Backup and Migration

Use the repository migration helper:

```text
scripts/db_backup_and_migrate.sh
```

### Backup First (required)

```bash
export DB_CONTAINER=<postgres_container>
export PGUSER=postgres
export PGDATABASE=silent_frequency
./scripts/db_backup_and_migrate.sh backup
```

### Apply Migration

```bash
./scripts/db_backup_and_migrate.sh migrate
```

### Restore if Needed

```bash
./scripts/db_backup_and_migrate.sh restore
```

### Safety Rule

Before applying migrations:

1. create a backup
2. verify the target environment
3. confirm rollback readiness
4. apply the migration only with explicit approval

---

## 4. Post-migration / Post-change Checklist

After feature-flag, migration, or behavior-affecting changes:

1. run smoke tests for:
   - `GET /api/sessions/{id}/game-state`
   - `POST /api/sessions/{id}/action`

2. verify event log growth for:
   - `game_action`
   - `puzzle_interaction_trace`
   - `attempt_submitted`

3. verify metrics counters:
   - `telemetry.game_action.count`
   - `telemetry.trace.truncated`
   - `telemetry.trace.too_large`

4. confirm no regression in canonical `POST /api/sessions/{id}/attempts` flow
5. confirm gameplay v2 modal attempts include `metadata.source="gameplay_v2"`

---

## 5. Scheduled Maintenance

### action_dedupe Cleanup Job

Cleanup script:

```text
backend/app/maintenance/cleanup_action_dedupe.py
```

### Dry Run

```bash
python -m backend.app.maintenance.cleanup_action_dedupe --days 30 --dry-run
```

### Execute Cleanup

```bash
python -m backend.app.maintenance.cleanup_action_dedupe --days 30 --batch-size 500
```

### Scheduling Guidance

- run via cron, systemd, or a containerized scheduled job
- recommended cadence: daily
- keep retention aligned with dedupe retry horizon, default 30 days

---

## 6. Known Phase-3 Test Triage (Not a Fix)

A common failure pattern is seed/content mismatch causing `tests/test_api_endpoints.py` failures.

### Reproduce

```bash
python -m pytest tests/test_api_endpoints.py -v
```

### Inspect

1. `backend/app/seed.py`
2. `backend/app/content/`
3. `backend/app/services/puzzle_service.py`
4. `backend/app/api/routes.py`

### Common Causes

- expected route contract differs from implemented endpoint shape
- seed content IDs no longer align with test fixtures
- old level/slot assumptions diverge from current backend-owned flow

### Important Note

This is a triage path, not a justification for compatibility hacks.

Prefer aligning tests and docs with the implemented canonical contract.

---

## 7. Batch 4.5 Integration QA Commands

```bash
python -m pytest -q \
   backend/app/tests/test_attempt_from_gameplay_v2.py \
   backend/app/tests/test_hint_count_and_trace_backend.py \
   backend/app/tests/test_trace_trimming_metrics.py \
   backend/app/tests/test_game_action_telemetry_exists.py
```

```bash
cd frontend && npm run test -- \
   tests/PuzzleScreen.409.test.tsx \
   tests/HintPanel.test.tsx \
   tests/Trace.cap.test.tsx
```

---

## 8. Operational Principles

- backend remains the canonical authority for gameplay and learning state
- gameplay v2 must remain behind explicit operational gating
- telemetry is for observation, not control
- canonical Phase-3 flow must remain stable even when gameplay v2 is disabled
- rollback should preserve research integrity and participant safety where possible

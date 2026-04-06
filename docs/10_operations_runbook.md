# Operations Runbook

## Scope

This runbook documents development and pilot-safe operational procedures for Silent Frequency.

## Feature Flag Control

Gameplay v2 must be controlled by a feature flag.

Recommended environments:

- staging: enabled for controlled validation
- production: disabled by default until approved

## Enable Gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=true
uvicorn backend.app.main:app --reload
```

## Disable Gameplay v2

```bash
export GAMEPLAY_V2_ENABLED=false
uvicorn backend.app.main:app --reload
```

## Rollback Strategy

If gameplay v2 causes instability:

1. disable gameplay v2 globally
2. stop issuing new gameplay v2 sessions
3. keep canonical Phase-3 flow available
4. allow pilot sessions to finish when safe
5. use admin intervention only for hard rollback cases

## Database Safety

Before applying migrations:

1. create a backup
2. verify the target environment
3. confirm rollback readiness
4. apply the migration with explicit approval

## Migration Commands

```bash
export DB_CONTAINER=<postgres_container>
export PGUSER=postgres
export PGDATABASE=silent_frequency

./scripts/db_backup_and_migrate.sh backup
./scripts/db_backup_and_migrate.sh migrate
./scripts/db_backup_and_migrate.sh restore
```

## Post-change Validation

After feature-flag, migration, or behavior-affecting changes:

1. smoke test gameplay v2 endpoints
2. verify canonical attempt flow still works
3. verify telemetry appears
4. inspect metrics counters
5. confirm no frontend regression in critical screens

## Scheduled Maintenance

The action dedupe cleanup job should be documented, scheduled, and reviewed periodically.

## Incident Rule

Do not invent new runtime behavior during incident response. Prefer disabling the experimental path and preserving canonical Phase-3 operation.

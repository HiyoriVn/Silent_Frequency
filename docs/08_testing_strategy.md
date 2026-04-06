# Testing Strategy

## Goals

The testing strategy ensures that:

- canonical session flow remains stable
- gameplay v2 behavior is safe and recoverable
- telemetry contracts remain valid
- frontend and backend stay aligned

## Test Layers

### Unit Tests

Used for:

- BKT logic
- content selection
- schema validation
- isolated service logic

### Integration Tests

Used for:

- API endpoint behavior
- session progression
- gameplay v2 flows
- telemetry creation

### Frontend Tests

Used for:

- rendering behavior
- user interactions
- conflict handling
- hint and trace-related UI behavior

### Manual E2E Validation

Used for:

- full loop verification
- setup sanity checks
- staging or demo validation

## Recommended Commands

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

### Frontend Validation

```bash
cd frontend
npm run lint
npm run test
```

## Manual Session Loop Validation

Verify the canonical loop:

1. create session
2. request next puzzle
3. submit attempt
4. repeat until completion
5. confirm the 9-step progression order
6. compare adaptive vs static behavior
7. verify mastery updates

## Gameplay v2 Validation

When gameplay v2 changes are involved, also verify:

- `GET /game-state` returns canonical snapshots
- `POST /action` returns typed effects
- stale-state handling produces recoverable UI behavior
- telemetry is emitted with expected fields
- canonical `POST /attempts` flow remains intact

## Definition of Done

A change is not complete until:

- relevant automated tests pass
- impacted manual checks are documented
- docs are updated
- frontend/backend contract alignment is confirmed

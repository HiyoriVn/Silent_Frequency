# Documentation Index

This folder contains the canonical engineering, research, and operations documentation for Silent Frequency.

## Recommended Reading Order

For new contributors:

1. `01_project_overview.md`
2. `02_local_setup.md`
3. `03_architecture_overview.md`
4. `04_session_and_gameplay_flow.md`
5. `08_testing_strategy.md`
6. `13_copilot_workflow.md`

For backend contributors:

- `03_architecture_overview.md`
- `04_session_and_gameplay_flow.md`
- `05_api_contracts.md`
- `09_telemetry_and_experiment_logging.md`
- `10_operations_runbook.md`

For frontend contributors:

- `03_architecture_overview.md`
- `05_api_contracts.md`
- `07_frontend_flow_and_ui.md`
- `08_testing_strategy.md`

For research and thesis work:

- `11_research_protocol.md`
- `12_pilot_and_evaluation_plan.md`
- `09_telemetry_and_experiment_logging.md`

## Documentation Principles

- Backend is the source of truth for progression, scoring, completion, and canonical gameplay state.
- Frontend is responsible for rendering, interaction, and transport only.
- Gameplay v2 is additive and experimental. It must not silently replace canonical Phase-3 behavior.
- Telemetry is observational and must never affect scoring, progression, or BKT updates.
- Contract changes must update docs, tests, and typed API surfaces together.

## When Documentation Must Be Updated

Update documentation whenever:

- an API request or response changes
- session progression or gameplay behavior changes
- telemetry payloads or thresholds change
- setup, migration, or rollback steps change
- research or pilot procedures change

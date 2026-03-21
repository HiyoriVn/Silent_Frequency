-- Batch 4.0 gameplay_v2 additive schema changes (PostgreSQL)

ALTER TABLE game_sessions
ADD COLUMN IF NOT EXISTS mode VARCHAR(16) NOT NULL DEFAULT 'phase3';

ALTER TABLE game_state
ADD COLUMN IF NOT EXISTS game_state_version INTEGER NOT NULL DEFAULT 0;

CREATE TABLE IF NOT EXISTS room_templates (
  id SERIAL PRIMARY KEY,
  room_id VARCHAR(64) NOT NULL UNIQUE,
  payload JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS action_dedupe (
  id SERIAL PRIMARY KEY,
  session_id UUID NOT NULL REFERENCES game_sessions(id),
  client_action_id UUID NOT NULL,
  response_json JSONB NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_action_dedupe_session_client UNIQUE (session_id, client_action_id)
);

CREATE INDEX IF NOT EXISTS ix_action_dedupe_session ON action_dedupe(session_id);

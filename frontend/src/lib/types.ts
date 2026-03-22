/**
 * Silent Frequency — TypeScript API Types
 *
 * Mirrors the Pydantic schemas defined in backend/app/api/schemas.py.
 */

// ── Shared envelope ──────────────────────────────────────

export type DifficultyTier = "low" | "mid" | "high";

export interface ApiMeta {
  timestamp: string;
  session_id: string;
}

export interface ApiError {
  code: string;
  message: string;
}

export interface ApiResponse<T = unknown> {
  ok: boolean;
  data: T | null;
  error: ApiError | null;
  meta: ApiMeta | null;
  /** Populated by api.ts for non-2xx responses; undefined for 2xx. */
  _http_status?: number;
}

// ── POST /api/sessions ──────────────────────────────────

export interface MasterySnapshot {
  vocabulary: number;
  grammar: number;
  listening: number;
}

export interface SessionCreated {
  session_id: string;
  player_id: string;
  session_token: string;
  condition: "adaptive" | "static";
  mode: "phase3" | "gameplay_v2";
  current_level_index: number;
  mastery: MasterySnapshot;
  current_room: string;
}

// ── GET /api/sessions/{id}/mastery ──────────────────────

export interface MasteryDetail {
  skill: string;
  p_learned: number;
  update_count: number;
  difficulty_tier: DifficultyTier;
}

export interface MasteryResponse {
  session_id: string;
  mastery: MasteryDetail[];
  summary: MasterySnapshot;
}

// ── GET /api/sessions/{id}/next-puzzle ───────────────────

export interface NextPuzzleResponse {
  puzzle_id: string;
  variant_id: string;
  skill: string;
  slot_order: number;
  difficulty_tier: DifficultyTier;
  prompt_text: string;
  audio_url: string | null;
  time_limit_sec: number | null;
  interaction_mode: "plain" | "scene_hotspot";
  interaction: Phase3InteractionPayload | null;
  hints?: string[];
  max_hints_shown?: number | null;
  max_attempt_chars?: number | null;
  session_complete: boolean;
}

// ── POST /api/sessions/{id}/attempts ────────────────────

export interface SubmitAttemptRequest {
  variant_id: string;
  answer: string;
  response_time_ms: number;
  hint_count_used: number;
  interaction_trace?: InteractionTrace | null;
  game_state_version?: number;
  metadata?: {
    source: string;
  };
}

export interface AttemptFeedback {
  is_correct: boolean;
  correct_answers: string[];
  p_learned_before: number;
  p_learned_after: number;
  difficulty_tier: DifficultyTier;
  current_level_index: number;
  session_complete: boolean;
  mastery: MasterySnapshot;
}

// ── Interaction types (optional) ───────────────────────

export interface Phase3InteractionScene {
  scene_id: string;
  asset_key: string;
  instruction_text?: string;
}

export interface Phase3InteractionRectShape {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface Phase3InteractionHotspotTrigger {
  trigger_type: "click";
  prompt_ref?: string | null;
}

export interface Phase3InteractionHotspot {
  hotspot_id: string;
  label?: string;
  shape_type: "rect";
  shape: Phase3InteractionRectShape;
  trigger: Phase3InteractionHotspotTrigger;
}

export interface Phase3InteractionPrompt {
  prompt_text: string;
  answer_type: "text";
  correct_answers: string[];
  max_attempt_chars?: number;
}

export interface Phase3InteractionPayload {
  interaction_version: 1;
  scene: Phase3InteractionScene;
  hotspots: Phase3InteractionHotspot[];
  prompts: Record<string, Phase3InteractionPrompt>;
  ui_hints?: {
    allow_reopen_prompt?: boolean;
    show_hotspot_labels?: boolean;
  };
}

export interface InteractionTraceEvent {
  event_type:
    | "hotspot_clicked"
    | "prompt_opened"
    | "prompt_closed"
    | "hint_opened";
  hotspot_id?: string;
  prompt_ref?: string;
  hint_id?: string;
  elapsed_ms: number;
}

export interface InteractionTrace {
  version?: number;
  type?: "interaction_trace";
  puzzle_id?: string;
  variant_id?: string;
  trace: InteractionTraceEvent[];
  response_time_ms?: number;
  _truncated_client?: boolean;
}

// ── Gameplay v2 interaction schema ─────────────────────

export type InteractionAction =
  | "use_item"
  | "inspect"
  | "take_item"
  | "open_object";

export interface Item {
  id: string;
  display_name: string;
  category: string;
  consumed: boolean;
  properties: Record<string, unknown>;
}

export interface GameStateObject {
  id: string;
  type: string;
  state: string;
  properties: Record<string, unknown>;
}

export interface GameStateSnapshot {
  interaction_schema_version: 2;
  session_id: string;
  game_state_version: number;
  updated_at: string;
  room_id: string;
  room_state: GameStateObject[];
  inventory: Item[];
  active_puzzles: string[];
  hint_policy?: {
    idle_seconds?: number;
    failed_attempts_threshold?: number;
  } | null;
}

export interface InteractionEffect {
  type: "add_item" | "unlock" | "show_dialogue" | "open_puzzle";
  target_id?: string | null;
  item_id?: string | null;
  puzzle_id?: string | null;
  dialogue_id?: string | null;
  dialogue_text?: string | null;
}

export interface InteractionHotspot {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  target_id: string;
  default_action?: InteractionAction;
}

export interface InteractionPayload {
  interaction_schema_version: 2;
  action: InteractionAction;
  target_id: string;
  item_id?: string;
  client_action_id?: string;
  client_ts?: string | number;
  game_state_version?: number;
  interaction_trace?: InteractionTrace;
}

export interface ActionResponseData {
  effects: InteractionEffect[];
  game_state: GameStateSnapshot;
}

// ── UI types (frontend-only) ────────────────────────────

export type Skill = "vocabulary" | "grammar" | "listening";

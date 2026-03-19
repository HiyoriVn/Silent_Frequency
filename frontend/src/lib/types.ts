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
  interaction: InteractionPayload | null;
  session_complete: boolean;
}

// ── POST /api/sessions/{id}/attempts ────────────────────

export interface SubmitAttemptRequest {
  variant_id: string;
  answer: string;
  response_time_ms: number;
  hint_count_used: number;
  interaction_trace?: InteractionTraceEvent[] | null;
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

export interface InteractionScene {
  scene_id: string;
  asset_key: string;
  instruction_text?: string;
}

export interface InteractionRectShape {
  x: number;
  y: number;
  width: number;
  height: number;
}

export interface InteractionHotspotTrigger {
  trigger_type: "click";
  prompt_ref?: string | null;
}

export interface InteractionHotspot {
  hotspot_id: string;
  label?: string;
  shape_type: "rect";
  shape: InteractionRectShape;
  trigger: InteractionHotspotTrigger;
}

export interface InteractionPrompt {
  prompt_text: string;
  answer_type: "text";
  correct_answers: string[];
  max_attempt_chars?: number;
}

export interface InteractionPayload {
  interaction_version: 1;
  scene: InteractionScene;
  hotspots: InteractionHotspot[];
  prompts: Record<string, InteractionPrompt>;
  ui_hints?: {
    allow_reopen_prompt?: boolean;
    show_hotspot_labels?: boolean;
  };
}

export interface InteractionTraceEvent {
  event_type: "hotspot_clicked" | "prompt_opened" | "prompt_closed";
  hotspot_id?: string;
  prompt_ref?: string;
  elapsed_ms: number;
}

// ── UI types (frontend-only) ────────────────────────────

export type Skill = "vocabulary" | "grammar" | "listening";

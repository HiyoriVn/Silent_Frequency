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

// ── GET /api/sessions/{id}/next-item ────────────────────

export interface NextItemResponse {
  puzzle_id: string;
  variant_id: string;
  skill: string;
  difficulty_tier: DifficultyTier;
  prompt_text: string;
  audio_url: string | null;
  time_limit_sec: number | null;
  fallback_used: boolean;
}

// ── POST /api/sessions/{id}/attempts ────────────────────

export interface SubmitAttemptRequest {
  variant_id: string;
  answer: string;
  response_time_ms: number;
  hint_count_used: number;
}

export interface AttemptFeedback {
  is_correct: boolean;
  correct_answers: string[];
  p_learned_before: number;
  p_learned_after: number;
  difficulty_tier: DifficultyTier;
  mastery: MasterySnapshot;
}

// ── UI types (frontend-only) ────────────────────────────

export type Skill = "vocabulary" | "grammar" | "listening";

export type GamePhase = "vocabulary" | "grammar" | "listening" | "completion";

export const SKILL_ORDER: Skill[] = ["vocabulary", "grammar", "listening"];

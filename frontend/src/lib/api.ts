/**
 * Silent Frequency — API Client
 *
 * Thin fetch wrappers for every backend endpoint.
 * Base URL defaults to http://localhost:8000 (FastAPI dev server).
 */

import type {
  ApiResponse,
  SessionCreated,
  MasteryResponse,
  NextPuzzleResponse,
  AttemptFeedback,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
console.log("API URL:", BASE);

// ── helpers ──────────────────────────────────────────────

async function request<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResponse<T>> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });

  // FastAPI wraps errors in the envelope too (via HTTPException detail)
  const json = await res.json();

  // If the server returned a non-2xx but the body is the envelope, just return it.
  if (!res.ok && json?.ok === false) return json as ApiResponse<T>;

  // Unexpected error (network, etc.)
  if (!res.ok) {
    return {
      ok: false,
      data: null,
      error: { code: "HTTP_ERROR", message: `HTTP ${res.status}` },
      meta: null,
    };
  }

  return json as ApiResponse<T>;
}

// ── endpoints ────────────────────────────────────────────

export async function createSession(
  displayName: string,
  condition: "adaptive" | "static" = "adaptive",
) {
  return request<SessionCreated>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ display_name: displayName, condition }),
  });
}

export async function getMastery(sessionId: string) {
  return request<MasteryResponse>(`/api/sessions/${sessionId}/mastery`);
}

export async function getNextPuzzle(sessionId: string) {
  return request<NextPuzzleResponse>(`/api/sessions/${sessionId}/next-puzzle`);
}

export async function submitAttempt(
  sessionId: string,
  body: {
    variant_id: string;
    answer: string;
    response_time_ms: number;
    hint_count_used: number;
  },
) {
  return request<AttemptFeedback>(`/api/sessions/${sessionId}/attempts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

/**
 * Silent Frequency — API Client
 *
 * Thin fetch wrappers for every backend endpoint.
 * Base URL defaults to http://localhost:8000 (FastAPI dev server).
 */

import type {
  ApiResponse,
  AuthResponseData,
  LogoutResponseData,
  SelfAssessedLevel,
  SessionCreated,
  MasteryResponse,
  NextPuzzleResponse,
  AttemptFeedback,
  SubmitAttemptRequest,
  ActionResponseData,
  GameStateSnapshot,
  InteractionTrace,
} from "./types";

type ActionRequestPayload = {
  interaction_schema_version: 2;
  action:
    | "use_item"
    | "inspect"
    | "take_item"
    | "open_object"
    | "open_sub_view"
    | "collect"
    | "navigation";
  target_id: string;
  item_id?: string;
  client_action_id?: string;
  client_ts?: string | number;
  game_state_version?: number;
  interaction_trace?: InteractionTrace;
};

const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

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
  // Preserve HTTP status so callers can detect 409 specifically.
  if (!res.ok && json?.ok === false) {
    return { ...json, _http_status: res.status } as ApiResponse<T>;
  }

  // Unexpected error (network, etc.)
  if (!res.ok) {
    return {
      ok: false,
      data: null,
      error: { code: "HTTP_ERROR", message: `HTTP ${res.status}` },
      meta: null,
      _http_status: res.status,
    };
  }

  return json as ApiResponse<T>;
}

// ── endpoints ────────────────────────────────────────────

export async function registerUser(
  username: string,
  password: string,
  realName?: string,
) {
  return request<AuthResponseData>("/api/auth/register", {
    method: "POST",
    body: JSON.stringify({
      username,
      password,
      real_name: realName?.trim() || undefined,
    }),
  });
}

export async function loginUser(username: string, password: string) {
  return request<AuthResponseData>("/api/auth/login", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
}

export async function logoutUser(authToken: string) {
  return request<LogoutResponseData>("/api/auth/logout", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${authToken}`,
    },
  });
}

export async function createSession(
  displayName: string,
  condition: "adaptive" | "static" = "adaptive",
  mode: "phase3" | "gameplay_v2" = "phase3",
  selfAssessedLevel?: SelfAssessedLevel,
) {
  return request<SessionCreated>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({
      display_name: displayName,
      condition,
      mode,
      self_assessed_level: selfAssessedLevel,
    }),
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
  body: SubmitAttemptRequest,
) {
  return request<AttemptFeedback>(`/api/sessions/${sessionId}/attempts`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

function buildClientActionId(): string | undefined {
  if (typeof globalThis.crypto?.randomUUID === "function") {
    return globalThis.crypto.randomUUID();
  }
  return undefined;
}

export async function getGameState(sessionId: string) {
  return request<{ game_state: GameStateSnapshot }>(
    `/api/sessions/${sessionId}/game-state`,
  );
}

export async function postAction(
  sessionId: string,
  body: ActionRequestPayload,
) {
  const payload: ActionRequestPayload = {
    ...body,
    client_action_id: body.client_action_id ?? buildClientActionId(),
  };

  return request<ActionResponseData>(`/api/sessions/${sessionId}/action`, {
    method: "POST",
    body: JSON.stringify(payload),
  });
}

/**
 * Silent Frequency — Zustand Game Store
 *
 * Single store that mirrors server state on the client.
 * The server is the source of truth; the store is a read-only cache
 * updated after every API call.
 */

import { create } from "zustand";
import type {
  MasterySnapshot,
  NextPuzzleResponse,
  AttemptFeedback,
} from "@/lib/types";
import * as api from "@/lib/api";

// ── State shape ──────────────────────────────────────────

interface GameState {
  // Session
  sessionId: string | null;
  playerName: string;
  condition: "adaptive" | "static";
  currentLevelIndex: number;
  sessionComplete: boolean;

  // Mastery (server mirror)
  mastery: MasterySnapshot;

  // Current puzzle
  currentItem: NextPuzzleResponse | null;

  // UI
  loading: boolean;
  error: string | null;
  lastFeedback: AttemptFeedback | null;

  // Puzzle attempt tracking
  startTime: number | null; // performance.now() when puzzle shown

  // Actions
  startSession: (name: string) => Promise<void>;
  fetchNextPuzzle: () => Promise<void>;
  submitAnswer: (answer: string, hintCount?: number) => Promise<void>;
  reset: () => void;
}

const INITIAL_MASTERY: MasterySnapshot = {
  vocabulary: 0.1,
  grammar: 0.1,
  listening: 0.1,
};

// ── Store ────────────────────────────────────────────────

export const useGameStore = create<GameState>((set, get) => ({
  sessionId: null,
  playerName: "",
  condition: "adaptive",
  currentLevelIndex: 0,
  sessionComplete: false,
  mastery: { ...INITIAL_MASTERY },
  currentItem: null,
  loading: false,
  error: null,
  lastFeedback: null,
  startTime: null,

  // ── Start session ──────────────────────────────────────
  startSession: async (name) => {
    set({ loading: true, error: null, playerName: name });
    const res = await api.createSession(name);
    if (!res.ok || !res.data) {
      set({ loading: false, error: res.error?.message ?? "Failed to start" });
      return;
    }
    set({
      sessionId: res.data.session_id,
      condition: res.data.condition,
      currentLevelIndex: res.data.current_level_index,
      sessionComplete: false,
      mastery: res.data.mastery,
      loading: false,
    });
    // Immediately fetch first puzzle
    await get().fetchNextPuzzle();
  },

  // ── Fetch next puzzle ──────────────────────────────────
  fetchNextPuzzle: async () => {
    const { sessionId, sessionComplete } = get();
    if (!sessionId || sessionComplete) return;

    set({ loading: true, error: null, currentItem: null, lastFeedback: null });

    const res = await api.getNextPuzzle(sessionId);
    if (!res.ok || !res.data) {
      set({ loading: false, error: res.error?.message ?? "No items" });
      return;
    }

    if (res.data.session_complete) {
      set({
        currentItem: null,
        sessionComplete: true,
        loading: false,
        startTime: null,
      });
      return;
    }

    set({
      currentItem: res.data,
      loading: false,
      startTime: performance.now(),
    });
  },

  // ── Submit answer ──────────────────────────────────────
  submitAnswer: async (answer, hintCount = 0) => {
    const { sessionId, currentItem, startTime } = get();
    if (!sessionId || !currentItem) return;

    const elapsed = startTime ? Math.round(performance.now() - startTime) : 0;
    set({ loading: true, error: null });

    const res = await api.submitAttempt(sessionId, {
      variant_id: currentItem.variant_id,
      answer,
      response_time_ms: elapsed,
      hint_count_used: hintCount,
    });

    if (!res.ok || !res.data) {
      set({ loading: false, error: res.error?.message ?? "Submit failed" });
      return;
    }

    set({
      lastFeedback: res.data,
      mastery: res.data.mastery,
      currentLevelIndex: res.data.current_level_index,
      sessionComplete: res.data.session_complete,
      currentItem: res.data.session_complete ? null : currentItem,
      loading: false,
    });
  },

  // ── Reset ──────────────────────────────────────────────
  reset: () =>
    set({
      sessionId: null,
      playerName: "",
      condition: "adaptive",
      currentLevelIndex: 0,
      sessionComplete: false,
      mastery: { ...INITIAL_MASTERY },
      currentItem: null,
      loading: false,
      error: null,
      lastFeedback: null,
      startTime: null,
    }),
}));

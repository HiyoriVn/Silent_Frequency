/**
 * Silent Frequency — Zustand Game Store
 *
 * Single store that mirrors server state on the client.
 * The server is the source of truth; the store is a read-only cache
 * updated after every API call.
 */

import { create } from "zustand";
import type {
  GamePhase,
  MasterySnapshot,
  NextItemResponse,
  AttemptFeedback,
  Skill,
} from "@/lib/types";
import { SKILL_ORDER } from "@/lib/types";
import * as api from "@/lib/api";

// ── State shape ──────────────────────────────────────────

interface GameState {
  // Session
  sessionId: string | null;
  playerName: string;

  // Mastery (server mirror)
  mastery: MasterySnapshot;

  // Current puzzle
  currentItem: NextItemResponse | null;
  phase: GamePhase;
  phaseIndex: number; // 0-3

  // UI
  loading: boolean;
  error: string | null;
  lastFeedback: AttemptFeedback | null;

  // Puzzle attempt tracking
  startTime: number | null; // performance.now() when puzzle shown

  // Actions
  startSession: (name: string) => Promise<void>;
  fetchNextItem: () => Promise<void>;
  submitAnswer: (answer: string, hintCount?: number) => Promise<void>;
  advancePhase: () => void;
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
  mastery: { ...INITIAL_MASTERY },
  currentItem: null,
  phase: "vocabulary",
  phaseIndex: 0,
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
      mastery: res.data.mastery,
      loading: false,
      phase: "vocabulary",
      phaseIndex: 0,
    });
    // Immediately fetch first puzzle
    await get().fetchNextItem();
  },

  // ── Fetch next item ────────────────────────────────────
  fetchNextItem: async () => {
    const { sessionId, phase } = get();
    if (!sessionId || phase === "completion") return;

    const skill = phase as Skill;
    set({ loading: true, error: null, currentItem: null, lastFeedback: null });

    const res = await api.getNextItem(sessionId, skill);
    if (!res.ok || !res.data) {
      set({ loading: false, error: res.error?.message ?? "No items" });
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
      loading: false,
    });
  },

  // ── Advance phase ──────────────────────────────────────
  advancePhase: () => {
    const { phaseIndex } = get();
    const next = phaseIndex + 1;
    if (next >= SKILL_ORDER.length) {
      set({ phase: "completion", phaseIndex: next, currentItem: null });
    } else {
      set({ phase: SKILL_ORDER[next], phaseIndex: next });
      get().fetchNextItem();
    }
  },

  // ── Reset ──────────────────────────────────────────────
  reset: () =>
    set({
      sessionId: null,
      playerName: "",
      mastery: { ...INITIAL_MASTERY },
      currentItem: null,
      phase: "vocabulary",
      phaseIndex: 0,
      loading: false,
      error: null,
      lastFeedback: null,
      startTime: null,
    }),
}));

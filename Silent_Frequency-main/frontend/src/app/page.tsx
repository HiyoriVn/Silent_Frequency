/**
 * Silent Frequency — Main Game Page
 *
 * Backend-owned session flow page.
 * UI states:
 *   1) no session => lobby
 *   2) active session => current puzzle
 *   3) completed session => completion summary
 */

"use client";

import React, { useState } from "react";
import { useGameStore } from "@/stores/gameStore";
import { useAudio } from "@/hooks/useAudio";
import GlitchText from "@/components/GlitchText";
import VocabularyPhase from "@/components/phases/VocabularyPhase";
import GrammarPhase from "@/components/phases/GrammarPhase";
import ListeningPhase from "@/components/phases/ListeningPhase";
import CompletionPhase from "@/components/phases/CompletionPhase";

export default function Home() {
  const {
    sessionId,
    sessionComplete,
    currentItem,
    loading,
    error,
    startSession,
  } = useGameStore();
  const { startAmbient } = useAudio();
  const [nameInput, setNameInput] = useState("");

  // ── Lobby / name entry ────────────────────────────────
  if (!sessionId) {
    const handleStart = async (e: React.FormEvent) => {
      e.preventDefault();
      if (!nameInput.trim()) return;
      startAmbient();
      await startSession(nameInput.trim());
    };

    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-8 px-4">
        <div className="text-center">
          <GlitchText
            mastery={0.15}
            as="h1"
            className="text-5xl font-bold tracking-wider text-neutral-100"
          >
            SILENT FREQUENCY
          </GlitchText>
          <p className="mt-3 text-sm tracking-widest text-neutral-500">
            ADAPTIVE ESCAPE ROOM
          </p>
        </div>

        <form
          onSubmit={handleStart}
          className="flex w-full max-w-xs flex-col gap-3"
        >
          <input
            type="text"
            value={nameInput}
            onChange={(e) => setNameInput(e.target.value)}
            placeholder="Enter callsign…"
            maxLength={64}
            autoFocus
            className="rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-3 text-center font-mono text-neutral-100 placeholder:text-neutral-600 focus:border-cyan-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !nameInput.trim()}
            className="rounded-lg bg-cyan-600 py-3 font-medium tracking-wider text-white transition hover:bg-cyan-500 disabled:opacity-40"
          >
            {loading ? "CONNECTING…" : "BEGIN TRANSMISSION"}
          </button>
          {error && <p className="text-center text-xs text-red-400">{error}</p>}
        </form>
      </main>
    );
  }

  // ── Completion state ──────────────────────────────────
  if (sessionComplete) {
    return (
      <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
        <CompletionPhase />
      </main>
    );
  }

  // ── Active puzzle state ───────────────────────────────
  const skill = currentItem?.skill;

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
      {/* Backend level indicator */}
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        <span className="uppercase tracking-wider">Live Session</span>
        {skill && <span className="text-neutral-700">—</span>}
        {skill && (
          <span className="font-semibold uppercase tracking-wider text-cyan-400">
            {skill}
          </span>
        )}
      </div>

      {/* Loading state */}
      {loading && !currentItem && (
        <p className="animate-pulse text-sm text-neutral-500">
          Decoding signal…
        </p>
      )}

      {/* Puzzle component chosen from backend-provided skill */}
      {skill === "vocabulary" && <VocabularyPhase />}
      {skill === "grammar" && <GrammarPhase />}
      {skill === "listening" && <ListeningPhase />}

      {!loading && !currentItem && !sessionComplete && (
        <p className="text-sm text-neutral-500">Waiting for next puzzle...</p>
      )}
    </main>
  );
}

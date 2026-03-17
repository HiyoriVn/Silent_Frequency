/**
 * Silent Frequency — Main Game Page
 *
 * Orchestrates the 4 adaptive phases:
 *   1. Vocabulary  2. Grammar  3. Listening  4. Completion
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
  const { sessionId, phase, loading, error, startSession } = useGameStore();
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

  // ── Phase router ──────────────────────────────────────
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-6 px-4 py-12">
      {/* Phase indicator */}
      <div className="flex items-center gap-2 text-xs text-neutral-500">
        {["vocabulary", "grammar", "listening", "completion"].map((p, i) => (
          <React.Fragment key={p}>
            {i > 0 && <span className="text-neutral-700">—</span>}
            <span
              className={
                p === phase
                  ? "font-semibold uppercase tracking-wider text-cyan-400"
                  : "uppercase tracking-wider"
              }
            >
              {p}
            </span>
          </React.Fragment>
        ))}
      </div>

      {/* Loading state */}
      {loading &&
        !useGameStore.getState().currentItem &&
        phase !== "completion" && (
          <p className="animate-pulse text-sm text-neutral-500">
            Decoding signal…
          </p>
        )}

      {/* Phase components */}
      {phase === "vocabulary" && <VocabularyPhase />}
      {phase === "grammar" && <GrammarPhase />}
      {phase === "listening" && <ListeningPhase />}
      {phase === "completion" && <CompletionPhase />}
    </main>
  );
}

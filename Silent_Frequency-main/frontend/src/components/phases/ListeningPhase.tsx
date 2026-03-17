/**
 * ListeningPhase — Audio-based puzzle
 *
 * Uses the audio_url from the puzzle variant when available.
 * Falls back to text-only if there is no audio.
 */

"use client";

import React, { useState } from "react";
import PuzzleContainer from "@/components/PuzzleContainer";
import GlitchText from "@/components/GlitchText";
import { useGameStore } from "@/stores/gameStore";
import { useAudio } from "@/hooks/useAudio";

export default function ListeningPhase() {
  const {
    currentItem,
    mastery,
    lastFeedback,
    loading,
    submitAnswer,
    fetchNextPuzzle,
  } = useGameStore();
  const [input, setInput] = useState("");
  const { playSfx } = useAudio();

  if (!currentItem) return null;

  const skillMastery = mastery.listening;

  const handlePlay = () => {
    if (currentItem.audio_url) {
      playSfx(currentItem.audio_url, 0.8);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    await submitAnswer(input.trim());
    setInput("");
  };

  const handleNext = () => {
    fetchNextPuzzle();
  };

  return (
    <PuzzleContainer
      skill="listening"
      mastery={skillMastery}
      tier={currentItem.difficulty_tier}
      timeLimit={currentItem.time_limit_sec}
    >
      {/* Audio + prompt */}
      <div className="mb-6 text-center">
        {currentItem.audio_url && (
          <button
            onClick={handlePlay}
            className="mx-auto mb-4 flex items-center gap-2 rounded-full bg-purple-700/60 px-6 py-2 text-sm text-purple-200 transition hover:bg-purple-600/80"
          >
            <span className="text-xl">▶</span> Play Audio
          </button>
        )}
        <GlitchText
          mastery={skillMastery}
          as="p"
          className="text-lg text-neutral-300"
        >
          {currentItem.prompt_text}
        </GlitchText>
      </div>

      {/* Answer form */}
      {!lastFeedback ? (
        <form onSubmit={handleSubmit} className="flex gap-3">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="What did you hear?"
            autoFocus
            disabled={loading}
            className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-neutral-100 placeholder:text-neutral-600 focus:border-purple-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-purple-600 px-5 py-2 font-medium text-white transition hover:bg-purple-500 disabled:opacity-40"
          >
            {loading ? "…" : "Submit"}
          </button>
        </form>
      ) : (
        <div className="space-y-4 text-center">
          <p
            className={`text-lg font-semibold ${lastFeedback.is_correct ? "text-green-400" : "text-red-400"}`}
          >
            {lastFeedback.is_correct ? "✓ Correct!" : "✗ Incorrect"}
          </p>
          {!lastFeedback.is_correct && (
            <p className="text-sm text-neutral-400">
              Answer:{" "}
              <span className="text-neutral-200">
                {lastFeedback.correct_answers.join(", ")}
              </span>
            </p>
          )}
          <p className="text-xs text-neutral-500">
            Mastery: {Math.round(lastFeedback.p_learned_before * 100)}% →{" "}
            {Math.round(lastFeedback.p_learned_after * 100)}%
          </p>
          <button
            onClick={handleNext}
            className="rounded-lg bg-neutral-700 px-6 py-2 text-sm text-neutral-200 transition hover:bg-neutral-600"
          >
            Next Puzzle →
          </button>
        </div>
      )}
    </PuzzleContainer>
  );
}

/**
 * GrammarPhase — Sentence correction / fill-in-the-blank puzzle
 *
 * Same interaction pattern as VocabularyPhase, different visual treatment.
 */

"use client";

import React, { useState } from "react";
import PuzzleContainer from "@/components/PuzzleContainer";
import GlitchText from "@/components/GlitchText";
import { useGameStore } from "@/stores/gameStore";

export default function GrammarPhase() {
  const {
    currentItem,
    mastery,
    lastFeedback,
    loading,
    submitAnswer,
    advancePhase,
    fetchNextItem,
  } = useGameStore();
  const [input, setInput] = useState("");

  if (!currentItem) return null;

  const skillMastery = mastery.grammar;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;
    await submitAnswer(input.trim());
    setInput("");
  };

  const handleNext = () => {
    if (lastFeedback && lastFeedback.p_learned_after >= 0.7) {
      advancePhase();
    } else {
      fetchNextItem();
    }
  };

  return (
    <PuzzleContainer
      skill="grammar"
      mastery={skillMastery}
      tier={currentItem.difficulty_tier}
      timeLimit={currentItem.time_limit_sec}
    >
      {/* Prompt */}
      <div className="mb-6 rounded-lg bg-neutral-800/60 p-4 text-center">
        <GlitchText
          mastery={skillMastery}
          as="p"
          className="font-mono text-lg text-neutral-200"
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
            placeholder="Complete the sentence…"
            autoFocus
            disabled={loading}
            className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 font-mono text-neutral-100 placeholder:text-neutral-600 focus:border-amber-500 focus:outline-none"
          />
          <button
            type="submit"
            disabled={loading || !input.trim()}
            className="rounded-lg bg-amber-600 px-5 py-2 font-medium text-white transition hover:bg-amber-500 disabled:opacity-40"
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
              <span className="font-mono text-neutral-200">
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
            {lastFeedback.p_learned_after >= 0.7
              ? "Next Phase →"
              : "Next Puzzle →"}
          </button>
        </div>
      )}
    </PuzzleContainer>
  );
}

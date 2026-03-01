/**
 * CompletionPhase — Game summary screen
 *
 * Shows final mastery across all three skills with a visual bar chart.
 */

"use client";

import React from "react";
import GlitchText from "@/components/GlitchText";
import { useGameStore } from "@/stores/gameStore";

const SKILLS = [
  { key: "vocabulary" as const, label: "Vocabulary", color: "bg-cyan-500" },
  { key: "grammar" as const, label: "Grammar", color: "bg-amber-500" },
  { key: "listening" as const, label: "Listening", color: "bg-purple-500" },
];

export default function CompletionPhase() {
  const { mastery, playerName, reset } = useGameStore();

  const avg = (mastery.vocabulary + mastery.grammar + mastery.listening) / 3;

  return (
    <div className="mx-auto w-full max-w-2xl rounded-2xl border-2 border-cyan-500/30 bg-neutral-900/80 p-8 text-center shadow-2xl backdrop-blur-sm">
      <GlitchText
        mastery={avg}
        as="h2"
        className="mb-2 text-3xl font-bold tracking-wider text-neutral-100"
      >
        SIGNAL DECODED
      </GlitchText>
      <p className="mb-8 text-sm text-neutral-500">
        Well done, <span className="text-neutral-300">{playerName}</span>.
        Transmission complete.
      </p>

      {/* Skill bars */}
      <div className="space-y-5">
        {SKILLS.map(({ key, label, color }) => {
          const pct = Math.round(mastery[key] * 100);
          return (
            <div key={key}>
              <div className="mb-1 flex items-center justify-between text-sm">
                <span className="text-neutral-400">{label}</span>
                <span className="font-mono text-neutral-300">{pct}%</span>
              </div>
              <div className="h-2 w-full overflow-hidden rounded-full bg-neutral-800">
                <div
                  className={`h-full rounded-full ${color} transition-all duration-1000`}
                  style={{ width: `${pct}%` }}
                />
              </div>
            </div>
          );
        })}
      </div>

      {/* Overall */}
      <p className="mt-8 text-xs text-neutral-600">
        Overall mastery:{" "}
        <span className="text-neutral-400">{Math.round(avg * 100)}%</span>
      </p>

      <button
        onClick={reset}
        className="mt-6 rounded-lg bg-neutral-700 px-8 py-2 text-sm text-neutral-200 transition hover:bg-neutral-600"
      >
        Play Again
      </button>
    </div>
  );
}

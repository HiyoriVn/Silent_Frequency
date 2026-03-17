/**
 * PuzzleContainer — adaptive wrapper for puzzle phases
 *
 * Adjusts visual treatment based on difficulty tier.
 * Shows mastery bar, timer countdown, and a consistent card layout.
 */

"use client";

import React from "react";
import GlitchText from "./GlitchText";
import type { DifficultyTier } from "@/lib/types";

interface PuzzleContainerProps {
  skill: string;
  mastery: number;
  tier: DifficultyTier;
  timeLimit: number | null;
  children: React.ReactNode;
}

const TIER_BORDER: Record<DifficultyTier, string> = {
  low: "border-green-500/40",
  mid: "border-amber-500/40",
  high: "border-red-500/40",
};

const TIER_LABEL: Record<DifficultyTier, string> = {
  low: "Beginner",
  mid: "Intermediate",
  high: "Advanced",
};

export default function PuzzleContainer({
  skill,
  mastery,
  tier,
  timeLimit,
  children,
}: PuzzleContainerProps) {
  return (
    <div
      className={`
        relative mx-auto w-full max-w-2xl rounded-2xl border-2
        bg-neutral-900/80 p-6 shadow-2xl backdrop-blur-sm
        transition-colors duration-500
        ${TIER_BORDER[tier]}
      `}
    >
      {/* Header bar */}
      <div className="mb-4 flex items-center justify-between text-sm">
        <GlitchText
          mastery={mastery}
          className="font-mono text-lg uppercase tracking-widest text-neutral-300"
        >
          {skill}
        </GlitchText>

        <div className="flex items-center gap-3">
          <span className="rounded-full bg-neutral-800 px-3 py-0.5 text-xs text-neutral-400">
            {TIER_LABEL[tier]}
          </span>
          {timeLimit && (
            <span className="font-mono text-xs text-neutral-500">
              {timeLimit}s
            </span>
          )}
        </div>
      </div>

      {/* Mastery bar */}
      <div className="mb-6 h-1 w-full overflow-hidden rounded-full bg-neutral-800">
        <div
          className="h-full rounded-full bg-cyan-500 transition-all duration-700"
          style={{ width: `${Math.round(mastery * 100)}%` }}
        />
      </div>

      {/* Puzzle body */}
      <div className="min-h-50">{children}</div>
    </div>
  );
}

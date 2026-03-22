"use client";

import React from "react";

interface HintPanelProps {
  hints: string[];
  attemptKey: string;
  maxHintsShown?: number | null;
  onHintOpened: (hintId: string) => void;
  onHintCountChange: (count: number) => void;
}

export default function HintPanel({
  hints,
  attemptKey,
  maxHintsShown,
  onHintOpened,
  onHintCountChange,
}: HintPanelProps) {
  const [revealed, setRevealed] = React.useState<Set<string>>(new Set());

  React.useEffect(() => {
    setRevealed(new Set());
    onHintCountChange(0);
  }, [attemptKey, onHintCountChange]);

  const revealLimit =
    typeof maxHintsShown === "number" && maxHintsShown >= 0
      ? maxHintsShown
      : hints.length;

  const revealHint = (hintId: string) => {
    setRevealed((prev) => {
      if (prev.has(hintId)) {
        return prev;
      }
      if (prev.size >= revealLimit) {
        return prev;
      }
      const next = new Set(prev);
      next.add(hintId);
      onHintOpened(hintId);
      onHintCountChange(next.size);
      return next;
    });
  };

  if (hints.length === 0) {
    return (
      <div className="rounded-lg border border-neutral-700 bg-neutral-900/80 p-4">
        <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-neutral-300">
          Hints
        </h3>
        <p className="text-xs text-neutral-500">No hints for this puzzle.</p>
      </div>
    );
  }

  return (
    <div className="rounded-lg border border-neutral-700 bg-neutral-900/80 p-4">
      <h3 className="mb-2 text-sm font-semibold uppercase tracking-wider text-neutral-300">
        Hints ({revealed.size}/{revealLimit})
      </h3>
      <ul className="space-y-2">
        {hints.map((hint, index) => {
          const hintId = `hint_${index + 1}`;
          const isRevealed = revealed.has(hintId);
          const revealBlocked = !isRevealed && revealed.size >= revealLimit;
          return (
            <li
              key={hintId}
              className="rounded-md border border-neutral-700 bg-neutral-800/60 p-2"
            >
              <div className="mb-2 flex items-center justify-between">
                <span className="text-xs text-neutral-300">
                  Hint {index + 1}
                </span>
                <button
                  type="button"
                  onClick={() => revealHint(hintId)}
                  disabled={revealBlocked}
                  className="text-xs text-cyan-300 disabled:text-neutral-600"
                >
                  {isRevealed ? "Revealed" : "Reveal"}
                </button>
              </div>
              {isRevealed && <p className="text-xs text-neutral-400">{hint}</p>}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

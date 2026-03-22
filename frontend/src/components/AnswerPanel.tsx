"use client";

import React from "react";

interface AnswerPanelProps {
  answer: string;
  maxAttemptChars?: number | null;
  disabled?: boolean;
  onChange: (value: string) => void;
  onSubmit: () => void;
}

export default function AnswerPanel({
  answer,
  maxAttemptChars,
  disabled,
  onChange,
  onSubmit,
}: AnswerPanelProps) {
  const maxLen =
    typeof maxAttemptChars === "number" && maxAttemptChars > 0
      ? maxAttemptChars
      : undefined;

  return (
    <div className="space-y-2">
      <input
        type="text"
        value={answer}
        maxLength={maxLen}
        onChange={(event) => onChange(event.target.value)}
        className="w-full rounded-md border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100"
        placeholder="Submit answer via POST /attempts"
      />
      <div className="flex items-center justify-between">
        <p className="text-xs text-neutral-500">
          {maxLen ? `${answer.length}/${maxLen}` : `${answer.length} chars`}
        </p>
        <button
          type="button"
          onClick={onSubmit}
          disabled={disabled || !answer.trim()}
          className="rounded-md bg-cyan-600 px-4 py-2 text-sm text-white disabled:opacity-50"
        >
          Submit
        </button>
      </div>
    </div>
  );
}

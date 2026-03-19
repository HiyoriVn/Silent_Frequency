"use client";

import React, { useRef, useState } from "react";
import PuzzleContainer from "@/components/PuzzleContainer";
import SceneRenderer from "@/components/SceneRenderer";
import { useGameStore } from "@/stores/gameStore";
import type { InteractionHotspot, InteractionTraceEvent } from "@/lib/types";

interface AnswerPanelProps {
  answer: string;
  loading: boolean;
  placeholder: string;
  onChange: (value: string) => void;
  onSubmit: (e: React.FormEvent) => void;
}

function AnswerPanel({
  answer,
  loading,
  placeholder,
  onChange,
  onSubmit,
}: AnswerPanelProps) {
  return (
    <form onSubmit={onSubmit} className="flex gap-3">
      <input
        type="text"
        value={answer}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        autoFocus
        disabled={loading}
        className="flex-1 rounded-lg border border-neutral-700 bg-neutral-800 px-4 py-2 text-neutral-100 placeholder:text-neutral-600 focus:border-cyan-500 focus:outline-none"
      />
      <button
        type="submit"
        disabled={loading || !answer.trim()}
        className="rounded-lg bg-cyan-600 px-5 py-2 font-medium text-white transition hover:bg-cyan-500 disabled:opacity-40"
      >
        {loading ? "..." : "Submit"}
      </button>
    </form>
  );
}

export default function PuzzleScreen() {
  const {
    currentItem,
    mastery,
    lastFeedback,
    loading,
    submitAnswer,
    fetchNextPuzzle,
  } = useGameStore();

  const [answer, setAnswer] = useState("");
  const [activeHotspotId, setActiveHotspotId] = useState<string | null>(null);
  const [openedPromptRef, setOpenedPromptRef] = useState<string | null>(null);
  const [interactionTrace, setInteractionTrace] = useState<
    InteractionTraceEvent[]
  >([]);
  const traceStartMs = useRef<number>(0);

  if (!currentItem) return null;

  const skillMastery =
    currentItem.skill === "vocabulary"
      ? mastery.vocabulary
      : currentItem.skill === "grammar"
        ? mastery.grammar
        : mastery.listening;

  const isInteractive =
    currentItem.interaction_mode === "scene_hotspot" &&
    currentItem.interaction !== null;

  const currentPromptText = !isInteractive
    ? currentItem.prompt_text
    : openedPromptRef && currentItem.interaction
      ? (currentItem.interaction.prompts[openedPromptRef]?.prompt_text ?? "")
      : "";

  const canAnswer = !isInteractive || Boolean(openedPromptRef);

  const appendTrace = (event: Omit<InteractionTraceEvent, "elapsed_ms">) => {
    const now = performance.now();
    if (traceStartMs.current === 0) {
      traceStartMs.current = now;
    }
    const elapsedMs = Math.max(0, Math.round(now - traceStartMs.current));
    setInteractionTrace((prev) => [
      ...prev,
      {
        ...event,
        elapsed_ms: elapsedMs,
      },
    ]);
  };

  const handleHotspotClick = (
    hotspot: InteractionHotspot,
    promptRef?: string,
  ) => {
    setActiveHotspotId(hotspot.hotspot_id);
    appendTrace({
      event_type: "hotspot_clicked",
      hotspot_id: hotspot.hotspot_id,
      prompt_ref: promptRef,
    });

    if (promptRef) {
      setOpenedPromptRef(promptRef);
      appendTrace({
        event_type: "prompt_opened",
        hotspot_id: hotspot.hotspot_id,
        prompt_ref: promptRef,
      });
    }
  };

  const handleClosePrompt = () => {
    if (!openedPromptRef) return;
    appendTrace({ event_type: "prompt_closed", prompt_ref: openedPromptRef });
    setOpenedPromptRef(null);
    setAnswer("");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!canAnswer || !answer.trim()) return;

    await submitAnswer(
      answer.trim(),
      0,
      interactionTrace.length > 0 ? interactionTrace : undefined,
    );
    setAnswer("");
  };

  return (
    <PuzzleContainer
      skill={currentItem.skill}
      mastery={skillMastery}
      tier={currentItem.difficulty_tier}
      timeLimit={currentItem.time_limit_sec}
    >
      {isInteractive && currentItem.interaction ? (
        <>
          <SceneRenderer
            interaction={currentItem.interaction}
            activeHotspotId={activeHotspotId}
            onHotspotClick={handleHotspotClick}
          />

          <div className="mb-4 text-sm text-neutral-400">
            {openedPromptRef
              ? currentPromptText
              : "Click a hotspot to reveal the prompt."}
          </div>

          {openedPromptRef && !lastFeedback && (
            <div className="mb-4">
              <button
                type="button"
                onClick={handleClosePrompt}
                className="rounded-md border border-neutral-700 px-3 py-1 text-xs text-neutral-300 hover:bg-neutral-800"
              >
                Close Prompt
              </button>
            </div>
          )}
        </>
      ) : (
        <div className="mb-6 text-center text-lg text-neutral-200">
          {currentItem.prompt_text}
        </div>
      )}

      {!lastFeedback ? (
        canAnswer ? (
          <AnswerPanel
            answer={answer}
            loading={loading}
            placeholder="Type your answer..."
            onChange={setAnswer}
            onSubmit={handleSubmit}
          />
        ) : (
          <div className="rounded-md border border-neutral-700 bg-neutral-800/60 p-3 text-sm text-neutral-400">
            Input is locked until a prompt hotspot is selected.
          </div>
        )
      ) : (
        <div className="space-y-4 text-center">
          <p
            className={`text-lg font-semibold ${
              lastFeedback.is_correct ? "text-green-400" : "text-red-400"
            }`}
          >
            {lastFeedback.is_correct ? "Correct" : "Incorrect"}
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
            Mastery: {Math.round(lastFeedback.p_learned_before * 100)}%{" -> "}
            {Math.round(lastFeedback.p_learned_after * 100)}%
          </p>
          <button
            onClick={() => fetchNextPuzzle()}
            className="rounded-lg bg-neutral-700 px-6 py-2 text-sm text-neutral-200 transition hover:bg-neutral-600"
          >
            Next Puzzle
          </button>
        </div>
      )}
    </PuzzleContainer>
  );
}

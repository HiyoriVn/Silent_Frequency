"use client";

import React from "react";
import AnswerPanel from "@/components/AnswerPanel";
import HintPanel from "@/components/HintPanel";
import InventoryPanel from "@/components/InventoryPanel";
import SceneRenderer from "@/components/SceneRenderer";
import {
  getGameState,
  getNextPuzzle,
  postAction,
  submitAttempt,
} from "@/lib/api";
import type {
  InteractionAction,
  GameStateObject,
  InteractionTrace,
  GameStateSnapshot,
  InteractionEffect,
  InteractionTraceEvent,
  NextPuzzleResponse,
} from "@/lib/types";

type SceneHotspot = {
  id: string;
  label: string;
  x: number;
  y: number;
  w: number;
  h: number;
  target_id: string;
  action?: InteractionAction;
  default_action?: "use_item" | "inspect" | "take_item" | "open_object";
  clickable?: boolean;
};

interface PuzzleScreenProps {
  sessionId: string;
}

interface ActivePuzzleModal {
  puzzleId: string;
  puzzle: NextPuzzleResponse;
  title: string;
}

interface AttemptResultBanner {
  status: "success" | "error";
  message: string;
}

type TraceEventInput = {
  event_type: InteractionTraceEvent["event_type"];
  hotspot_id?: string;
  prompt_ref?: string;
  hint_id?: string;
};

const ROOM404_VIEW_ASSET_KEYS: Record<string, string> = {
  patient_room_404__bg_01_bed_wall: "placeholder_room404_bed_wall",
  patient_room_404__bg_04_door_side: "placeholder_room404_door_side",
  patient_room_404__sub_bedside_drawer: "placeholder_room404_bedside_drawer",
};

const ROOM404_HOTSPOT_LAYOUTS: Record<
  string,
  { x: number; y: number; w: number; h: number }
> = {
  bedside_table: { x: 0.6, y: 0.5, w: 0.24, h: 0.26 },
  folded_note: { x: 0.34, y: 0.24, w: 0.22, h: 0.2 },
  warning_sign: { x: 0.2, y: 0.26, w: 0.22, h: 0.24 },
  main_door: { x: 0.74, y: 0.15, w: 0.2, h: 0.7 },
};

const ROOM404_HOTSPOT_LABELS: Record<string, string> = {
  bedside_table: "Bedside Table",
  folded_note: "Folded Note",
  warning_sign: "Warning Sign",
  main_door: "Main Door",
};

const ROOM404_PUZZLE_TITLES: Record<string, string> = {
  p_warning_sign_translate: "Warning Sign Translation",
};

const ROOM404_PUZZLE_PROMPTS: Record<string, string> = {
  p_warning_sign_translate:
    "The warning sign text is partially faded. Translate its key safety phrase into clear English.",
};

const ROOM404_WARNING_SIGN_PUZZLE_ID = "p_warning_sign_translate";

function toTitleLabel(id: string): string {
  return id
    .replaceAll("__", " ")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function getPuzzleTitle(puzzleId: string): string {
  return ROOM404_PUZZLE_TITLES[puzzleId] ?? toTitleLabel(puzzleId);
}

function buildFallbackPuzzleById(puzzleId: string): NextPuzzleResponse {
  return {
    puzzle_id: puzzleId,
    variant_id: `${puzzleId}__fallback`,
    skill: "vocabulary",
    slot_order: 0,
    difficulty_tier: "mid",
    prompt_text:
      ROOM404_PUZZLE_PROMPTS[puzzleId] ??
      "Puzzle prompt is unavailable. You can still enter an answer for the next batch wiring.",
    audio_url: null,
    time_limit_sec: null,
    interaction_mode: "plain",
    interaction: null,
    hints: ["Focus on the key warning phrase.", "Use concise natural English."],
    max_hints_shown: 2,
    max_attempt_chars: 120,
    session_complete: false,
  };
}

function toUserFacingError(
  code?: string,
  message?: string,
  status?: number,
): string {
  if (code === "MODE_DISABLED") {
    return "Gameplay v2 is disabled on the API. Set GAMEPLAY_V2_ENABLED=true and restart uvicorn.";
  }
  if (code === "MODE_MISMATCH") {
    return "This session is not gameplay_v2. Start a new gameplay_v2 session.";
  }
  if (status === 403) {
    return message ?? "Access denied for this session endpoint.";
  }
  return message ?? "Request failed";
}

function extractHotspots(objects: GameStateObject[]): SceneHotspot[] {
  const hotspots: SceneHotspot[] = [];

  for (const obj of objects) {
    const hotspot =
      typeof obj.properties === "object" && obj.properties !== null
        ? (obj.properties.hotspot as Record<string, unknown> | undefined)
        : undefined;

    if (!hotspot) continue;
    const x = Number(hotspot.x);
    const y = Number(hotspot.y);
    const w = Number(hotspot.w);
    const h = Number(hotspot.h);
    if ([x, y, w, h].some((v) => Number.isNaN(v))) continue;

    const label = typeof hotspot.label === "string" ? hotspot.label : obj.id;
    const defaultAction =
      typeof hotspot.default_action === "string"
        ? hotspot.default_action
        : undefined;

    const normalizedAction: InteractionAction =
      defaultAction === "use_item" ||
      defaultAction === "inspect" ||
      defaultAction === "take_item" ||
      defaultAction === "open_object"
        ? defaultAction
        : "inspect";

    hotspots.push({
      id: obj.id,
      label,
      x,
      y,
      w,
      h,
      target_id: obj.id,
      action: normalizedAction,
      clickable: true,
    });
  }

  return hotspots;
}

function resolveCanonicalHotspotAction(
  actionHint: string | null | undefined,
  type: string,
): InteractionAction {
  if (actionHint === "open_sub_view") return "open_sub_view";
  if (actionHint === "collect") return "collect";
  if (actionHint === "navigation") return "navigation";
  if (actionHint === "open_puzzle") return "inspect";
  if (actionHint === "inspect") return "inspect";
  if (type === "navigation") return "navigation";
  return "inspect";
}

function normalizeInteractionAction(
  action: string | null | undefined,
): InteractionAction {
  if (action === "use_item") return "use_item";
  if (action === "inspect") return "inspect";
  if (action === "take_item") return "take_item";
  if (action === "open_object") return "open_object";
  if (action === "open_sub_view") return "open_sub_view";
  if (action === "collect") return "collect";
  if (action === "navigation") return "navigation";
  return "inspect";
}

function extractCanonicalRoom404Hotspots(
  snapshot: GameStateSnapshot,
): SceneHotspot[] {
  if (!Array.isArray(snapshot.hotspots) || snapshot.hotspots.length === 0) {
    // Compatibility fallback for non-canonical snapshots/tests only.
    return extractHotspots(snapshot.room_state ?? []);
  }

  return snapshot.hotspots
    .filter((hotspot) => hotspot.visible)
    .map((hotspot) => {
      const layout = ROOM404_HOTSPOT_LAYOUTS[hotspot.id] ?? {
        x: 0.08,
        y: 0.08,
        w: 0.2,
        h: 0.2,
      };

      return {
        id: hotspot.id,
        label: ROOM404_HOTSPOT_LABELS[hotspot.id] ?? toTitleLabel(hotspot.id),
        x: layout.x,
        y: layout.y,
        w: layout.w,
        h: layout.h,
        target_id: hotspot.id,
        action: resolveCanonicalHotspotAction(
          hotspot.action_hint,
          hotspot.type,
        ),
        clickable: Boolean(hotspot.clickable),
      };
    });
}

export default function PuzzleScreen({ sessionId }: PuzzleScreenProps) {
  const [snapshot, setSnapshot] = React.useState<GameStateSnapshot | null>(
    null,
  );
  const [effects, setEffects] = React.useState<InteractionEffect[]>([]);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);
  const [activeHotspotId, setActiveHotspotId] = React.useState<string | null>(
    null,
  );
  const [selectedItemId, setSelectedItemId] = React.useState<string | null>(
    null,
  );
  const [trace, setTrace] = React.useState<InteractionTraceEvent[]>([]);
  const [hintCountUsed, setHintCountUsed] = React.useState(0);
  const [modal, setModal] = React.useState<ActivePuzzleModal | null>(null);
  const [attemptKey, setAttemptKey] = React.useState("attempt-0");
  const [attemptAnswer, setAttemptAnswer] = React.useState("");
  const [attemptResult, setAttemptResult] =
    React.useState<AttemptResultBanner | null>(null);
  const [staleBanner, setStaleBanner] = React.useState(false);
  const retryHandlerRef = React.useRef<(() => void) | null>(null);
  const traceStartRef = React.useRef<number>(0);

  const MAX_TRACE_EVENTS = 20;

  const resetAttemptTrace = React.useCallback(() => {
    setTrace([]);
    setHintCountUsed(0);
    setAttemptKey(`attempt-${Date.now()}`);
    traceStartRef.current = 0;
  }, []);

  const appendTrace = React.useCallback((event: TraceEventInput) => {
    const now = performance.now();
    if (traceStartRef.current === 0) {
      traceStartRef.current = now;
    }
    const elapsed = Math.max(0, Math.round(now - traceStartRef.current));
    const nextEvent: InteractionTraceEvent = {
      ...event,
      elapsed_ms: elapsed,
    };
    setTrace((prev) => {
      if (prev.length >= MAX_TRACE_EVENTS) {
        return prev;
      }
      return [...prev, nextEvent];
    });
  }, []);

  const showStaleStateBanner = React.useCallback((retry?: () => void) => {
    retryHandlerRef.current = retry ?? null;
    setStaleBanner(true);
  }, []);

  const refreshSnapshot = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await getGameState(sessionId);
    if (!response.ok || !response.data) {
      setError(
        toUserFacingError(
          response.error?.code,
          response.error?.message,
          response._http_status,
        ),
      );
      setLoading(false);
      return;
    }
    setSnapshot(response.data.game_state);
    setLoading(false);
  }, [sessionId]);

  React.useEffect(() => {
    void refreshSnapshot();
  }, [refreshSnapshot]);

  const loadPuzzleById = React.useCallback(
    async (puzzleId: string): Promise<NextPuzzleResponse> => {
      // Compatibility transport: backend currently exposes next-puzzle endpoint.
      const nextPuzzleRes = await getNextPuzzle(sessionId);
      if (nextPuzzleRes.ok && nextPuzzleRes.data) {
        if (nextPuzzleRes.data.puzzle_id === puzzleId) {
          return nextPuzzleRes.data;
        }
      }
      return buildFallbackPuzzleById(puzzleId);
    },
    [sessionId],
  );

  const maybeOpenPuzzleModal = React.useCallback(
    async (orderedEffects: InteractionEffect[]) => {
      const openPuzzle = orderedEffects.find(
        (effect) => effect.type === "open_puzzle",
      );
      if (!openPuzzle?.puzzle_id) return;
      const puzzleId = openPuzzle.puzzle_id;
      const puzzlePayload = await loadPuzzleById(puzzleId);

      resetAttemptTrace();
      setAttemptResult(null);
      setAttemptAnswer("");
      setModal({
        puzzleId,
        puzzle: puzzlePayload,
        title: getPuzzleTitle(puzzleId),
      });
      appendTrace({
        event_type: "prompt_opened",
        prompt_ref: puzzleId,
      });
    },
    [appendTrace, loadPuzzleById, resetAttemptTrace],
  );

  const runAction = React.useCallback(
    async (payload: {
      action: InteractionAction;
      target_id: string;
      item_id?: string;
    }) => {
      if (!snapshot) return;

      setLoading(true);
      setError(null);
      setStaleBanner(false);

      const currentTrace = trace.slice(0, MAX_TRACE_EVENTS);

      const response = await postAction(sessionId, {
        interaction_schema_version: 2,
        action: payload.action,
        target_id: payload.target_id,
        item_id: payload.item_id,
        game_state_version: snapshot.game_state_version,
        ...(currentTrace.length > 0
          ? {
              interaction_trace: {
                version: 1,
                type: "interaction_trace" as const,
                trace: currentTrace,
              },
            }
          : {}),
      });

      // Handle 409 stale-state: reconcile from snapshot, show banner, let user retry manually.
      if (response._http_status === 409) {
        // eslint-disable-next-line @typescript-eslint/no-explicit-any
        const snap = (response as Record<string, any>).data_snapshot;
        if (snap) {
          setSnapshot(snap);
        } else {
          await refreshSnapshot();
        }
        showStaleStateBanner();
        setLoading(false);
        return;
      }

      if (!response.ok || !response.data) {
        setError(
          toUserFacingError(
            response.error?.code,
            response.error?.message,
            response._http_status,
          ),
        );
        setLoading(false);
        return;
      }

      const orderedEffects = response.data.effects ?? [];
      setEffects(orderedEffects);
      setSnapshot(response.data.game_state);
      setLoading(false);
      await maybeOpenPuzzleModal(orderedEffects);
    },
    [
      maybeOpenPuzzleModal,
      refreshSnapshot,
      sessionId,
      showStaleStateBanner,
      snapshot,
      trace,
    ],
  );

  const handleHotspotClicked = async (hotspot: SceneHotspot) => {
    setActiveHotspotId(hotspot.id);
    appendTrace({ event_type: "hotspot_clicked", hotspot_id: hotspot.id });

    const resolvedAction = normalizeInteractionAction(
      hotspot.action ?? hotspot.default_action,
    );
    const canClick = hotspot.clickable ?? true;

    if (!canClick && resolvedAction !== "navigation") {
      return;
    }

    if (selectedItemId) {
      await runAction({
        action: "use_item",
        target_id: hotspot.target_id,
        item_id: selectedItemId,
      });
      setSelectedItemId(null);
      return;
    }

    if (resolvedAction === "inspect") {
      appendTrace({ event_type: "prompt_opened", hotspot_id: hotspot.id });
    }

    await runAction({
      action: resolvedAction,
      target_id: hotspot.target_id,
    });
  };

  const submitPuzzleAttempt = async () => {
    if (!modal || !attemptAnswer.trim()) return;
    setLoading(true);
    setError(null);
    setAttemptResult(null);

    const responseTimeMs =
      trace.length > 0 ? trace[trace.length - 1].elapsed_ms : 0;

    const interactionTracePayload: InteractionTrace | undefined =
      trace.length > 0
        ? {
            version: 1,
            type: "interaction_trace",
            puzzle_id: modal.puzzleId ?? undefined,
            variant_id: modal.puzzle.variant_id ?? undefined,
            trace: trace.slice(0, MAX_TRACE_EVENTS),
            response_time_ms: responseTimeMs ?? undefined,
          }
        : undefined;

    const result = await submitAttempt(sessionId, {
      puzzle_id: modal.puzzleId,
      variant_id: modal.puzzle.variant_id,
      answer: attemptAnswer.trim(),
      response_time_ms: responseTimeMs,
      hint_count_used: hintCountUsed,
      interaction_trace: interactionTracePayload,
      game_state_version: snapshot?.game_state_version,
      metadata: { source: "gameplay_v2" },
    });

    if (result._http_status === 409) {
      await refreshSnapshot();
      showStaleStateBanner(() => {
        setModal((prev) => prev);
      });
      setLoading(false);
      return;
    }

    if (!result.ok) {
      setError(result.error?.message ?? "Attempt failed");
      setLoading(false);
      return;
    }

    if (result.data?.is_correct) {
      setAttemptResult({
        status: "success",
        message: "Correct answer. Puzzle resolved.",
      });
      appendTrace({
        event_type: "prompt_closed",
        prompt_ref: result.data.puzzle_id,
      });
    } else {
      setAttemptResult({
        status: "error",
        message: "Incorrect answer. Try again.",
      });
    }

    setTrace([]);
    traceStartRef.current = 0;
    setLoading(false);
    await refreshSnapshot();
  };

  const hotspots = snapshot ? extractCanonicalRoom404Hotspots(snapshot) : [];
  const activeViewId = snapshot
    ? (snapshot.sub_view_id ??
      snapshot.current_background_view_id ??
      snapshot.view_id)
    : "patient_room_404__bg_01_bed_wall";
  const assetKey = ROOM404_VIEW_ASSET_KEYS[activeViewId] ?? activeViewId;
  const foldedNoteCollected = Boolean(snapshot?.flags?.bedside_note_collected);
  const doorUnlocked = Boolean(snapshot?.flags?.room404_exit_unlocked);
  const firstLanguageInteractionDone = Boolean(
    snapshot?.flags?.first_language_interaction_done,
  );
  const warningSignPuzzleActive = Boolean(
    snapshot?.active_puzzles?.includes(ROOM404_WARNING_SIGN_PUZZLE_ID),
  );
  const warningSignPuzzleStatus = doorUnlocked
    ? "Solved"
    : warningSignPuzzleActive
      ? "In progress"
      : "Not solved";
  const isSubViewOpen = Boolean(snapshot?.sub_view_id);

  return (
    <section className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
      <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-4">
        <h2 className="mb-3 text-sm uppercase tracking-wider text-neutral-400">
          Gameplay v2 Room: {snapshot?.room_id ?? "..."}
        </h2>
        <p className="mb-2 text-xs text-neutral-500">View: {activeViewId}</p>

        {!isSubViewOpen && (
          <div className="mb-3 flex flex-wrap gap-2">
            <button
              type="button"
              onClick={() =>
                void runAction({
                  action: "navigation",
                  target_id: "patient_room_404__bg_01_bed_wall",
                })
              }
              className="rounded border border-neutral-600 px-2 py-1 text-xs text-neutral-300"
            >
              Bed Wall View
            </button>
            <button
              type="button"
              onClick={() =>
                void runAction({
                  action: "navigation",
                  target_id: "patient_room_404__bg_04_door_side",
                })
              }
              className="rounded border border-neutral-600 px-2 py-1 text-xs text-neutral-300"
            >
              Door Side View
            </button>
          </div>
        )}

        {isSubViewOpen && (
          <div className="mb-3">
            <button
              type="button"
              onClick={() =>
                void runAction({
                  action: "navigation",
                  target_id:
                    snapshot?.current_background_view_id ??
                    "patient_room_404__bg_01_bed_wall",
                })
              }
              className="rounded border border-neutral-600 px-2 py-1 text-xs text-neutral-300"
            >
              Back To Main View
            </button>
          </div>
        )}

        {loading && (
          <p className="mb-3 text-sm text-neutral-500">Syncing state...</p>
        )}
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        {staleBanner && (
          <div className="mb-3 flex items-center justify-between rounded-md border border-amber-600/40 bg-amber-900/20 px-3 py-2 text-sm text-amber-300">
            <span>State updated. Your action did not apply. Please retry.</span>
            <button
              type="button"
              onClick={() => {
                setStaleBanner(false);
                retryHandlerRef.current?.();
              }}
              className="ml-2 text-xs text-amber-500 hover:text-amber-200"
            >
              Retry
            </button>
          </div>
        )}

        {snapshot && (
          <SceneRenderer
            assetKey={assetKey}
            hotspots={hotspots}
            activeHotspotId={activeHotspotId}
            onHotspotClicked={handleHotspotClicked}
          />
        )}

        <div className="mt-4 space-y-2 text-xs text-neutral-400">
          <p>State Version: {snapshot?.game_state_version ?? 0}</p>
        </div>

        <div className="mt-4 rounded-md border border-neutral-700 bg-neutral-800/60 p-3">
          <h3 className="mb-2 text-xs uppercase tracking-wider text-neutral-300">
            Room 404 Progress
          </h3>
          <ul className="space-y-1 text-xs text-neutral-400">
            <li>Warning Sign Puzzle: {warningSignPuzzleStatus}</li>
            <li>Main Door: {doorUnlocked ? "Unlocked" : "Locked"}</li>
            <li>
              Language Interaction:{" "}
              {firstLanguageInteractionDone ? "Done" : "Not done"}
            </li>
            <li>
              Folded Note: {foldedNoteCollected ? "Collected" : "Not collected"}
            </li>
          </ul>

          {selectedItemId && (
            <p className="text-cyan-300">
              Selected item: {selectedItemId}. Click a hotspot target to use it.
            </p>
          )}
        </div>

        {effects.length > 0 && (
          <div className="mt-4 rounded-md border border-neutral-700 bg-neutral-800/70 p-3">
            <h3 className="mb-2 text-xs uppercase tracking-wider text-neutral-300">
              Last Effects (Ordered)
            </h3>
            <ul className="space-y-1 text-xs text-neutral-400">
              {effects.map((effect, index) => (
                <li key={`${effect.type}-${index}`}>
                  {index + 1}. {effect.type}
                  {effect.target_id ? ` -> ${effect.target_id}` : ""}
                  {effect.puzzle_id ? ` -> ${effect.puzzle_id}` : ""}
                  {effect.dialogue_text ? ` (${effect.dialogue_text})` : ""}
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <div className="space-y-4">
        <InventoryPanel
          items={snapshot?.inventory ?? []}
          selectedItemId={selectedItemId}
          onSelectItem={setSelectedItemId}
          onClearSelection={() => setSelectedItemId(null)}
        />
      </div>

      {modal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Puzzle Modal"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4"
        >
          <div className="w-full max-w-lg rounded-lg border border-neutral-700 bg-neutral-900 p-5">
            <h3 className="mb-2 text-lg font-semibold text-neutral-100">
              {modal.title}
            </h3>
            <p className="mb-2 text-xs uppercase tracking-wider text-neutral-500">
              Puzzle ID: {modal.puzzleId}
            </p>
            <p className="mb-4 text-sm text-neutral-300">
              {modal.puzzle.prompt_text}
            </p>

            {attemptResult && (
              <p
                className={`mb-3 text-sm ${
                  attemptResult.status === "success"
                    ? "text-emerald-300"
                    : "text-rose-300"
                }`}
              >
                {attemptResult.message}
              </p>
            )}

            <div className="space-y-4">
              <HintPanel
                hints={modal.puzzle.hints ?? []}
                attemptKey={attemptKey}
                maxHintsShown={modal.puzzle.max_hints_shown}
                onHintOpened={(hintId) => {
                  appendTrace({
                    event_type: "hint_opened",
                    hint_id: hintId,
                    prompt_ref: modal.puzzle.variant_id,
                  });
                }}
                onHintCountChange={setHintCountUsed}
              />

              <AnswerPanel
                answer={attemptAnswer}
                maxAttemptChars={modal.puzzle.max_attempt_chars}
                disabled={loading}
                onChange={setAttemptAnswer}
                onSubmit={submitPuzzleAttempt}
              />
            </div>
            <button
              type="button"
              onClick={() => {
                setModal(null);
                setAttemptResult(null);
                setAttemptAnswer("");
              }}
              className="mt-3 text-xs text-neutral-500 hover:text-neutral-300"
            >
              Close
            </button>
          </div>
        </div>
      )}
    </section>
  );
}

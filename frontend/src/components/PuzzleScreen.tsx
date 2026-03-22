"use client";

import React from "react";
import InventoryPanel from "@/components/InventoryPanel";
import SceneRenderer from "@/components/SceneRenderer";
import {
  getGameState,
  getNextPuzzle,
  postAction,
  submitAttempt,
} from "@/lib/api";
import type {
  GameStateObject,
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
  default_action?: "use_item" | "inspect" | "take_item" | "open_object";
};

interface PuzzleScreenProps {
  sessionId: string;
}

interface ActivePuzzleModal {
  puzzleId: string;
  puzzle: NextPuzzleResponse;
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

    hotspots.push({
      id: obj.id,
      label,
      x,
      y,
      w,
      h,
      target_id: obj.id,
      default_action: defaultAction as SceneHotspot["default_action"],
    });
  }

  return hotspots;
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
  const [hintOpen, setHintOpen] = React.useState(false);
  const [modal, setModal] = React.useState<ActivePuzzleModal | null>(null);
  const [attemptAnswer, setAttemptAnswer] = React.useState("");
  const [staleBanner, setStaleBanner] = React.useState(false);
  const traceStartRef = React.useRef<number>(0);

  const MAX_TRACE_EVENTS = 20;

  const appendTrace = React.useCallback(
    (event: Omit<InteractionTraceEvent, "elapsed_ms">) => {
      const now = performance.now();
      if (traceStartRef.current === 0) {
        traceStartRef.current = now;
      }
      const elapsed = Math.max(0, Math.round(now - traceStartRef.current));
      setTrace((prev) => {
        if (prev.length >= MAX_TRACE_EVENTS) return prev;
        return [...prev, { ...event, elapsed_ms: elapsed }];
      });
    },
    [],
  );

  const refreshSnapshot = React.useCallback(async () => {
    setLoading(true);
    setError(null);
    const response = await getGameState(sessionId);
    if (!response.ok || !response.data) {
      setError(response.error?.message ?? "Failed to load game state");
      setLoading(false);
      return;
    }
    setSnapshot(response.data.game_state);
    setLoading(false);
  }, [sessionId]);

  React.useEffect(() => {
    void refreshSnapshot();
  }, [refreshSnapshot]);

  const maybeOpenPuzzleModal = React.useCallback(
    async (orderedEffects: InteractionEffect[]) => {
      const openPuzzle = orderedEffects.find(
        (effect) => effect.type === "open_puzzle",
      );
      if (!openPuzzle?.puzzle_id) return;

      appendTrace({
        event_type: "prompt_opened",
        prompt_ref: openPuzzle.puzzle_id,
      });
      const nextPuzzleRes = await getNextPuzzle(sessionId);
      if (!nextPuzzleRes.ok || !nextPuzzleRes.data) {
        setError(nextPuzzleRes.error?.message ?? "Failed to load puzzle");
        return;
      }

      setModal({
        puzzleId: openPuzzle.puzzle_id,
        puzzle: nextPuzzleRes.data,
      });
    },
    [appendTrace, sessionId],
  );

  const runAction = React.useCallback(
    async (payload: {
      action: "use_item" | "inspect" | "take_item" | "open_object";
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
        setStaleBanner(true);
        setLoading(false);
        return;
      }

      if (!response.ok || !response.data) {
        setError(response.error?.message ?? "Action failed");
        setLoading(false);
        return;
      }

      const orderedEffects = response.data.effects ?? [];
      setEffects(orderedEffects);
      setSnapshot(response.data.game_state);
      setTrace([]);
      traceStartRef.current = 0;
      setLoading(false);
      await maybeOpenPuzzleModal(orderedEffects);
    },
    [maybeOpenPuzzleModal, refreshSnapshot, sessionId, snapshot, trace],
  );

  const handleHotspotClicked = async (hotspot: SceneHotspot) => {
    setActiveHotspotId(hotspot.id);
    appendTrace({ event_type: "hotspot_clicked", hotspot_id: hotspot.id });

    if (selectedItemId) {
      await runAction({
        action: "use_item",
        target_id: hotspot.target_id,
        item_id: selectedItemId,
      });
      setSelectedItemId(null);
      return;
    }

    const action = hotspot.default_action ?? "inspect";
    if (action === "inspect") {
      appendTrace({ event_type: "prompt_opened", hotspot_id: hotspot.id });
    }

    await runAction({
      action,
      target_id: hotspot.target_id,
    });
  };

  const submitPuzzleAttempt = async () => {
    if (!modal || !attemptAnswer.trim()) return;
    setLoading(true);
    setError(null);

    const result = await submitAttempt(sessionId, {
      variant_id: modal.puzzle.variant_id,
      answer: attemptAnswer.trim(),
      response_time_ms: 0,
      hint_count_used: hintOpen ? 1 : 0,
      interaction_trace: trace.length > 0 ? trace : undefined,
    });

    if (!result.ok) {
      setError(result.error?.message ?? "Attempt failed");
      setLoading(false);
      return;
    }

    setModal(null);
    setAttemptAnswer("");
    setTrace([]);
    setHintOpen(false);
    setLoading(false);
    await refreshSnapshot();
  };

  const hotspots = snapshot ? extractHotspots(snapshot.room_state) : [];
  const assetKey = (() => {
    if (!snapshot) return "lab1-desk";
    const first = snapshot.room_state[0];
    const value = first?.properties?.asset_key;
    return typeof value === "string" ? value : "lab1-desk";
  })();

  return (
    <section className="mx-auto grid w-full max-w-6xl grid-cols-1 gap-4 lg:grid-cols-[2fr_1fr]">
      <div className="rounded-lg border border-neutral-700 bg-neutral-900 p-4">
        <h2 className="mb-3 text-sm uppercase tracking-wider text-neutral-400">
          Gameplay v2 Room: {snapshot?.room_id ?? "..."}
        </h2>

        {loading && (
          <p className="mb-3 text-sm text-neutral-500">Syncing state...</p>
        )}
        {error && <p className="mb-3 text-sm text-red-400">{error}</p>}
        {staleBanner && (
          <div className="mb-3 flex items-center justify-between rounded-md border border-amber-600/40 bg-amber-900/20 px-3 py-2 text-sm text-amber-300">
            <span>State updated — refreshed</span>
            <button
              type="button"
              onClick={() => setStaleBanner(false)}
              className="ml-2 text-xs text-amber-500 hover:text-amber-200"
            >
              Dismiss
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

        <div className="rounded-lg border border-neutral-700 bg-neutral-900/80 p-4">
          <div className="mb-2 flex items-center justify-between">
            <h3 className="text-sm font-semibold uppercase tracking-wider text-neutral-300">
              Hint
            </h3>
            <button
              type="button"
              onClick={() => {
                setHintOpen((prev) => !prev);
                if (!hintOpen) {
                  appendTrace({ event_type: "hint_opened" });
                }
              }}
              className="text-xs text-neutral-500 hover:text-neutral-300"
            >
              {hintOpen ? "Hide" : "Open"}
            </button>
          </div>
          {hintOpen && (
            <p className="text-xs text-neutral-400">
              Try inspecting the note, then collecting what you need from the
              drawer.
            </p>
          )}
        </div>
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
              Puzzle Opened: {modal.puzzleId}
            </h3>
            <p className="mb-4 text-sm text-neutral-300">
              {modal.puzzle.prompt_text}
            </p>

            <div className="flex gap-2">
              <input
                type="text"
                value={attemptAnswer}
                onChange={(event) => setAttemptAnswer(event.target.value)}
                className="flex-1 rounded-md border border-neutral-700 bg-neutral-800 px-3 py-2 text-sm text-neutral-100"
                placeholder="Submit answer via POST /attempts"
              />
              <button
                type="button"
                onClick={submitPuzzleAttempt}
                disabled={loading || !attemptAnswer.trim()}
                className="rounded-md bg-cyan-600 px-4 py-2 text-sm text-white disabled:opacity-50"
              >
                Submit
              </button>
            </div>
            <button
              type="button"
              onClick={() => setModal(null)}
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

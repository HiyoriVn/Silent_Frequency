import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import PuzzleScreen from "@/components/PuzzleScreen";

const getGameState = vi.fn();
const postAction = vi.fn();
const getNextPuzzle = vi.fn();
const submitAttempt = vi.fn();

vi.mock("@/lib/api", () => ({
  getGameState: (...args: unknown[]) => getGameState(...args),
  postAction: (...args: unknown[]) => postAction(...args),
  getNextPuzzle: (...args: unknown[]) => getNextPuzzle(...args),
  submitAttempt: (...args: unknown[]) => submitAttempt(...args),
}));

describe("Trace cap", () => {
  it("caps client interaction trace at 20 events in action payload", async () => {
    const snapshot = {
      interaction_schema_version: 2 as const,
      session_id: "session-1",
      game_state_version: 0,
      updated_at: new Date().toISOString(),
      room_id: "lab1",
      room_state: [
        {
          id: "old_radio",
          type: "interactable",
          state: "locked",
          properties: {
            hotspot: {
              x: 0.1,
              y: 0.2,
              w: 0.2,
              h: 0.2,
              label: "Old Radio",
              default_action: "inspect",
            },
            asset_key: "lab1-desk",
          },
        },
      ],
      inventory: [],
      active_puzzles: [],
      hint_policy: null,
    };

    getGameState.mockResolvedValue({
      ok: true,
      data: { game_state: snapshot },
    });
    // Keep requests non-success to avoid modal transitions while accumulating trace
    postAction.mockResolvedValue({
      ok: false,
      data: null,
      error: { code: "NOOP", message: "noop" },
      _http_status: 400,
    });

    render(<PuzzleScreen sessionId="session-1" />);

    const hotspot = await screen.findByRole("button", { name: "Old Radio" });
    for (let i = 0; i < 25; i += 1) {
      fireEvent.click(hotspot);
    }

    await waitFor(() => {
      expect(postAction).toHaveBeenCalled();
    });

    const lastCall = postAction.mock.calls[postAction.mock.calls.length - 1];
    const payload = lastCall?.[1];
    expect(payload).toBeTruthy();
    if (payload?.interaction_trace?.trace) {
      expect(payload.interaction_trace.trace.length).toBeLessThanOrEqual(20);
    }
  });
});

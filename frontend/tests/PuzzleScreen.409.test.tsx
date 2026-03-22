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

describe("PuzzleScreen stale state UX", () => {
  it("shows retry banner and refetches game state on action 409", async () => {
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
    postAction.mockResolvedValue({
      ok: false,
      data: null,
      error: { code: "STATE_MISMATCH", message: "client state stale" },
      _http_status: 409,
    });

    render(<PuzzleScreen sessionId="session-1" />);

    const hotspot = await screen.findByRole("button", { name: "Old Radio" });
    fireEvent.click(hotspot);

    await waitFor(() => {
      expect(getGameState).toHaveBeenCalledTimes(2);
    });

    expect(
      await screen.findByText(
        "State updated. Your action did not apply. Please retry.",
      ),
    ).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Retry" })).toBeInTheDocument();
  });
});

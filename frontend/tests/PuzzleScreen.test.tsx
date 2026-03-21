import React from "react";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, it, expect, vi } from "vitest";
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

describe("PuzzleScreen", () => {
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
    inventory: [
      {
        id: "bent_key",
        display_name: "Bent Key",
        category: "tool",
        consumed: false,
        properties: {},
      },
    ],
    active_puzzles: [],
    hint_policy: null,
  };

  beforeEach(() => {
    vi.clearAllMocks();
    getGameState.mockResolvedValue({
      ok: true,
      data: { game_state: snapshot },
    });
    postAction.mockResolvedValue({
      ok: true,
      data: {
        effects: [
          { type: "unlock", target_id: "old_radio" },
          { type: "open_puzzle", puzzle_id: "start_listen_code" },
        ],
        game_state: { ...snapshot, game_state_version: 1 },
      },
    });
    getNextPuzzle.mockResolvedValue({
      ok: true,
      data: {
        puzzle_id: "start_listen_code",
        variant_id: "start_listen_code_mid",
        skill: "listening",
        slot_order: 0,
        difficulty_tier: "mid",
        prompt_text: "Type the code",
        audio_url: null,
        time_limit_sec: null,
        interaction_mode: "plain",
        interaction: null,
        session_complete: false,
      },
    });
    submitAttempt.mockResolvedValue({ ok: true, data: { is_correct: true } });
  });

  it("loads canonical game-state and renders inventory", async () => {
    render(<PuzzleScreen sessionId="session-1" />);

    await waitFor(() => {
      expect(getGameState).toHaveBeenCalledWith("session-1");
    });

    expect(await screen.findByText("Bent Key")).toBeInTheDocument();
  });

  it("posts action then opens puzzle modal and submits attempt", async () => {
    render(<PuzzleScreen sessionId="session-1" />);

    const item = await screen.findByRole("button", { name: /Bent Key/i });
    fireEvent.click(item);

    const hotspot = await screen.findByRole("button", { name: "Old Radio" });
    fireEvent.click(hotspot);

    await waitFor(() => {
      expect(postAction).toHaveBeenCalledWith(
        "session-1",
        expect.objectContaining({
          action: "use_item",
          target_id: "old_radio",
          item_id: "bent_key",
          game_state_version: 0,
        }),
      );
    });

    expect(
      await screen.findByRole("dialog", { name: "Puzzle Modal" }),
    ).toBeInTheDocument();

    fireEvent.change(
      screen.getByPlaceholderText("Submit answer via POST /attempts"),
      {
        target: { value: "1234" },
      },
    );
    fireEvent.click(screen.getByRole("button", { name: "Submit" }));

    await waitFor(() => {
      expect(submitAttempt).toHaveBeenCalledWith(
        "session-1",
        expect.objectContaining({
          variant_id: "start_listen_code_mid",
          answer: "1234",
        }),
      );
    });
  });
});

import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import HintPanel from "@/components/HintPanel";

describe("HintPanel", () => {
  it("counts unique hint reveals and logs hint_opened once per hint", () => {
    const onHintOpened = vi.fn();
    const onHintCountChange = vi.fn();

    render(
      <HintPanel
        hints={["first", "second"]}
        attemptKey="attempt-1"
        onHintOpened={onHintOpened}
        onHintCountChange={onHintCountChange}
      />,
    );

    const revealButtons = screen.getAllByRole("button", { name: /reveal/i });

    fireEvent.click(revealButtons[0]);
    // Clicking same hint again should not increment unique count
    fireEvent.click(screen.getByRole("button", { name: /revealed/i }));
    fireEvent.click(revealButtons[1]);

    expect(onHintOpened).toHaveBeenCalledTimes(2);
    expect(onHintOpened).toHaveBeenNthCalledWith(1, "hint_1");
    expect(onHintOpened).toHaveBeenNthCalledWith(2, "hint_2");

    const countCalls = onHintCountChange.mock.calls.map((entry) => entry[0]);
    expect(countCalls).toContain(1);
    expect(countCalls).toContain(2);
  });
});

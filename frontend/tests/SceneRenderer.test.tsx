import React from "react";
import { fireEvent, render, screen } from "@testing-library/react";
import "@testing-library/jest-dom";
import { describe, it, expect, vi } from "vitest";
import SceneRenderer from "@/components/SceneRenderer";

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

describe("SceneRenderer", () => {
  const hotspots: SceneHotspot[] = [
    {
      id: "old_radio",
      label: "Old Radio",
      x: 0.1,
      y: 0.2,
      w: 0.3,
      h: 0.4,
      target_id: "old_radio",
      default_action: "inspect",
    },
  ];

  it("calls callback on click", () => {
    const onHotspotClicked = vi.fn();
    render(
      <SceneRenderer
        assetKey="lab1-desk"
        hotspots={hotspots}
        activeHotspotId={null}
        onHotspotClicked={onHotspotClicked}
      />,
    );

    const button = screen.getByRole("button", { name: "Old Radio" });
    fireEvent.click(button);
    expect(onHotspotClicked).toHaveBeenCalledWith(hotspots[0]);
  });

  it("supports keyboard activation", () => {
    const onHotspotClicked = vi.fn();
    render(
      <SceneRenderer
        assetKey="lab1-desk"
        hotspots={hotspots}
        activeHotspotId={null}
        onHotspotClicked={onHotspotClicked}
      />,
    );

    const button = screen.getByRole("button", { name: "Old Radio" });
    fireEvent.keyDown(button, { key: "Enter" });
    fireEvent.keyDown(button, { key: " " });

    expect(onHotspotClicked).toHaveBeenCalledTimes(2);
  });

  it("maps normalized coordinates to percentages", () => {
    render(
      <SceneRenderer
        assetKey="lab1-desk"
        hotspots={hotspots}
        activeHotspotId={null}
        onHotspotClicked={() => undefined}
      />,
    );

    const button = screen.getByRole("button", { name: "Old Radio" });
    expect(button).toHaveStyle({
      left: "10%",
      top: "20%",
      width: "30%",
      height: "40%",
    });
  });
});

/**
 * Silent Frequency — GlitchText Rendering Tests
 *
 * Tests the GlitchText component's glitch_level = 1 − mastery logic,
 * CSS custom property output, and boundary handling.
 *
 * Run with:  cd frontend && npx jest --config jest.config.ts
 *            or:  cd frontend && npx vitest run
 */

import React from "react";
import { render, screen } from "@testing-library/react";
import GlitchText from "@/components/GlitchText";
import "@testing-library/jest-dom";

// ══════════════════════════════════════
// 1. GLITCH LEVEL CALCULATION
// ══════════════════════════════════════

describe("GlitchText — glitch level = 1 − mastery", () => {
  it("renders children text", () => {
    render(<GlitchText mastery={0.5}>Hello</GlitchText>);
    expect(screen.getByText("Hello")).toBeInTheDocument();
  });

  it("sets data-text attribute for pseudo-element content", () => {
    render(<GlitchText mastery={0.5}>Signal</GlitchText>);
    const el = screen.getByText("Signal");
    expect(el.getAttribute("data-text")).toBe("Signal");
  });

  it("applies glitch-text CSS class", () => {
    render(<GlitchText mastery={0.5}>Test</GlitchText>);
    const el = screen.getByText("Test");
    expect(el.classList.contains("glitch-text")).toBe(true);
  });

  it("appends additional className", () => {
    render(
      <GlitchText mastery={0.5} className="font-bold text-red-500">
        Styled
      </GlitchText>,
    );
    const el = screen.getByText("Styled");
    expect(el.className).toContain("font-bold");
    expect(el.className).toContain("text-red-500");
  });
});

// ══════════════════════════════════════
// 2. CSS CUSTOM PROPERTIES
// ══════════════════════════════════════

describe("GlitchText — CSS custom properties", () => {
  it("sets --glitch = 1 − mastery when mastery is low (0.1)", () => {
    render(<GlitchText mastery={0.1}>Low</GlitchText>);
    const el = screen.getByText("Low");
    // glitch_level = 1 - 0.1 = 0.9 → intensity = 0.9 (> 0.05 threshold)
    expect(el.style.getPropertyValue("--glitch")).toBe("0.9");
    expect(el.style.getPropertyValue("--glitch-px")).toBe("7px"); // round(0.9 * 8) = 7
  });

  it("sets --glitch = 0.5 when mastery is 0.5", () => {
    render(<GlitchText mastery={0.5}>Mid</GlitchText>);
    const el = screen.getByText("Mid");
    expect(el.style.getPropertyValue("--glitch")).toBe("0.5");
    expect(el.style.getPropertyValue("--glitch-px")).toBe("4px"); // round(0.5 * 8) = 4
  });

  it("sets --glitch = 0 when mastery ≥ 0.95 (below 0.05 threshold)", () => {
    render(<GlitchText mastery={0.96}>High</GlitchText>);
    const el = screen.getByText("High");
    // glitch_level = 1 - 0.96 = 0.04 → below 0.05 threshold → intensity = 0
    expect(el.style.getPropertyValue("--glitch")).toBe("0");
    expect(el.style.getPropertyValue("--glitch-px")).toBe("0px");
  });

  it("sets --glitch = 1 when mastery is 0.0", () => {
    render(<GlitchText mastery={0.0}>Zero</GlitchText>);
    const el = screen.getByText("Zero");
    expect(el.style.getPropertyValue("--glitch")).toBe("1");
    expect(el.style.getPropertyValue("--glitch-px")).toBe("8px");
  });

  it("clamps mastery above 1.0 → --glitch = 0", () => {
    render(<GlitchText mastery={1.5}>Over</GlitchText>);
    const el = screen.getByText("Over");
    // max(0, min(1, 1 - 1.5)) = max(0, min(1, -0.5)) = max(0, -0.5) = 0
    expect(el.style.getPropertyValue("--glitch")).toBe("0");
  });

  it("clamps negative mastery → --glitch = 1", () => {
    render(<GlitchText mastery={-0.5}>Neg</GlitchText>);
    const el = screen.getByText("Neg");
    // max(0, min(1, 1 - (-0.5))) = max(0, min(1, 1.5)) = max(0, 1) = 1
    expect(el.style.getPropertyValue("--glitch")).toBe("1");
  });
});

// ══════════════════════════════════════
// 3. TAG RENDERING
// ══════════════════════════════════════

describe("GlitchText — polymorphic rendering", () => {
  it("renders as <span> by default", () => {
    render(<GlitchText mastery={0.5}>Default</GlitchText>);
    const el = screen.getByText("Default");
    expect(el.tagName).toBe("SPAN");
  });

  it("renders as <h1> when as='h1'", () => {
    render(
      <GlitchText mastery={0.5} as="h1">
        Heading
      </GlitchText>,
    );
    const el = screen.getByText("Heading");
    expect(el.tagName).toBe("H1");
  });

  it("renders as <p> when as='p'", () => {
    render(
      <GlitchText mastery={0.5} as="p">
        Paragraph
      </GlitchText>,
    );
    const el = screen.getByText("Paragraph");
    expect(el.tagName).toBe("P");
  });
});

// ══════════════════════════════════════
// 4. ADAPTIVE RENDERING SCENARIOS
// ══════════════════════════════════════

describe("GlitchText — adaptive rendering scenarios", () => {
  it("brand-new student (mastery=0.1) → heavy glitch", () => {
    render(<GlitchText mastery={0.1}>New</GlitchText>);
    const el = screen.getByText("New");
    const intensity = Number(el.style.getPropertyValue("--glitch"));
    expect(intensity).toBeGreaterThanOrEqual(0.8);
  });

  it("mid-progress student (mastery=0.5) → moderate glitch", () => {
    render(<GlitchText mastery={0.5}>Progress</GlitchText>);
    const el = screen.getByText("Progress");
    const intensity = Number(el.style.getPropertyValue("--glitch"));
    expect(intensity).toBeCloseTo(0.5, 1);
  });

  it("mastered student (mastery=0.95) → effect killed (threshold)", () => {
    render(<GlitchText mastery={0.95}>Master</GlitchText>);
    const el = screen.getByText("Master");
    // 1 - 0.95 = 0.05, exactly at threshold → killed to 0
    const intensity = Number(el.style.getPropertyValue("--glitch"));
    expect(intensity).toBe(0);
  });

  it("fully mastered (mastery=1.0) → no glitch at all", () => {
    render(<GlitchText mastery={1.0}>Clear</GlitchText>);
    const el = screen.getByText("Clear");
    expect(el.style.getPropertyValue("--glitch")).toBe("0");
    expect(el.style.getPropertyValue("--glitch-px")).toBe("0px");
  });
});

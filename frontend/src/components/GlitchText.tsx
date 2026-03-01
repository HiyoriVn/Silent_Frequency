/**
 * GlitchText — adaptive glitch effect
 *
 * glitch_level = 1 − mastery
 * When mastery is low the text glitches heavily; as the player improves
 * the text becomes clear.
 *
 * Uses CSS custom-property --glitch to drive animation intensity.
 */

"use client";

import React from "react";

interface GlitchTextProps {
  children: string;
  mastery: number; // 0 … 1
  as?: keyof React.JSX.IntrinsicElements;
  className?: string;
}

export default function GlitchText({
  children,
  mastery,
  as: Tag = "span",
  className = "",
}: GlitchTextProps) {
  const glitchLevel = Math.max(0, Math.min(1, 1 - mastery));
  const intensity = glitchLevel > 0.05 ? glitchLevel : 0; // kill effect at near-1 mastery

  return (
    <Tag
      className={`glitch-text ${className}`}
      style={
        {
          "--glitch": intensity,
          "--glitch-px": `${Math.round(intensity * 8)}px`,
        } as React.CSSProperties
      }
      data-text={children}
    >
      {children}
    </Tag>
  );
}

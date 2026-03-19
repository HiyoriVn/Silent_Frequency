"use client";

import React from "react";
import type { InteractionHotspot, InteractionPayload } from "@/lib/types";

interface SceneRendererProps {
  interaction: InteractionPayload;
  activeHotspotId: string | null;
  onHotspotClick: (hotspot: InteractionHotspot, promptRef?: string) => void;
}

export default function SceneRenderer({
  interaction,
  activeHotspotId,
  onHotspotClick,
}: SceneRendererProps) {
  return (
    <div className="mb-5">
      <div className="mb-2 text-xs uppercase tracking-wider text-neutral-500">
        Scene: {interaction.scene.scene_id}
      </div>

      <div className="relative h-64 w-full overflow-hidden rounded-lg border border-neutral-700 bg-neutral-800/70">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.08),transparent_45%),radial-gradient(circle_at_80%_70%,rgba(251,191,36,0.08),transparent_40%)]" />

        {interaction.hotspots.map((hotspot) => {
          const isActive = hotspot.hotspot_id === activeHotspotId;
          const rect = hotspot.shape;

          return (
            <button
              key={hotspot.hotspot_id}
              type="button"
              onClick={() =>
                onHotspotClick(hotspot, hotspot.trigger.prompt_ref ?? undefined)
              }
              className={`absolute border text-[10px] font-mono uppercase tracking-wider transition ${
                isActive
                  ? "border-cyan-300 bg-cyan-500/20 text-cyan-100"
                  : "border-cyan-600/80 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20"
              }`}
              style={{
                left: `${rect.x * 100}%`,
                top: `${rect.y * 100}%`,
                width: `${rect.width * 100}%`,
                height: `${rect.height * 100}%`,
              }}
            >
              {hotspot.label ?? hotspot.hotspot_id}
            </button>
          );
        })}
      </div>
    </div>
  );
}

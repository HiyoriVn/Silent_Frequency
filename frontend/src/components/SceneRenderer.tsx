"use client";

import React from "react";

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

interface SceneRendererProps {
  assetKey: string;
  hotspots: SceneHotspot[];
  activeHotspotId: string | null;
  onHotspotClicked: (hotspot: SceneHotspot) => void;
}

export default function SceneRenderer({
  assetKey,
  hotspots,
  activeHotspotId,
  onHotspotClicked,
}: SceneRendererProps) {
  const [imageFailed, setImageFailed] = React.useState(false);

  return (
    <div className="mb-5">
      <div className="relative h-64 w-full overflow-hidden rounded-lg border border-neutral-700 bg-neutral-800/70">
        {!imageFailed ? (
          <img
            src={`/scenes/${assetKey}.png`}
            alt="Escape room scene"
            className="absolute inset-0 h-full w-full object-cover"
            onError={() => setImageFailed(true)}
          />
        ) : (
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(34,211,238,0.08),transparent_45%),radial-gradient(circle_at_80%_70%,rgba(251,191,36,0.08),transparent_40%)]" />
        )}

        {hotspots.map((hotspot) => {
          const isActive = hotspot.id === activeHotspotId;

          return (
            <button
              key={hotspot.id}
              type="button"
              aria-label={hotspot.label}
              onClick={() => onHotspotClicked(hotspot)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onHotspotClicked(hotspot);
                }
              }}
              className={`absolute border text-[10px] font-mono uppercase tracking-wider transition ${
                isActive
                  ? "border-cyan-300 bg-cyan-500/20 text-cyan-100"
                  : "border-cyan-600/80 bg-cyan-500/10 text-cyan-300 hover:bg-cyan-500/20"
              }`}
              style={{
                left: `${hotspot.x * 100}%`,
                top: `${hotspot.y * 100}%`,
                width: `${hotspot.w * 100}%`,
                height: `${hotspot.h * 100}%`,
              }}
            >
              {hotspot.label}
            </button>
          );
        })}
      </div>
    </div>
  );
}

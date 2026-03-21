"use client";

import React from "react";
import type { Item } from "@/lib/types";

interface InventoryPanelProps {
  items: Item[];
  selectedItemId: string | null;
  onSelectItem: (itemId: string) => void;
  onClearSelection: () => void;
}

export default function InventoryPanel({
  items,
  selectedItemId,
  onSelectItem,
  onClearSelection,
}: InventoryPanelProps) {
  return (
    <aside className="rounded-lg border border-neutral-700 bg-neutral-900/80 p-4">
      <div className="mb-3 flex items-center justify-between">
        <h3 className="text-sm font-semibold uppercase tracking-wider text-neutral-300">
          Inventory
        </h3>
        <button
          type="button"
          onClick={onClearSelection}
          className="text-xs text-neutral-500 hover:text-neutral-300"
        >
          Clear
        </button>
      </div>

      {items.length === 0 ? (
        <p className="text-xs text-neutral-500">No items acquired.</p>
      ) : (
        <div className="grid grid-cols-1 gap-2">
          {items.map((item) => {
            const selected = item.id === selectedItemId;
            return (
              <button
                key={item.id}
                type="button"
                onClick={() => onSelectItem(item.id)}
                className={`rounded-md border px-3 py-2 text-left text-sm transition ${
                  selected
                    ? "border-cyan-400 bg-cyan-500/20 text-cyan-100"
                    : "border-neutral-700 bg-neutral-800/60 text-neutral-300 hover:border-neutral-500"
                }`}
                aria-pressed={selected}
              >
                <div className="font-medium">{item.display_name}</div>
                <div className="text-xs text-neutral-500">{item.category}</div>
              </button>
            );
          })}
        </div>
      )}
    </aside>
  );
}

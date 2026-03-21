"use client";

import React from "react";
import PuzzleScreen from "@/components/PuzzleScreen";
import { createSession } from "@/lib/api";

export default function Home() {
  const [displayName, setDisplayName] = React.useState("");
  const [sessionId, setSessionId] = React.useState<string | null>(null);
  const [loading, setLoading] = React.useState(false);
  const [error, setError] = React.useState<string | null>(null);

  const startGameplayV2 = async (event: React.FormEvent) => {
    event.preventDefault();
    if (!displayName.trim()) return;

    setLoading(true);
    setError(null);
    const response = await createSession(
      displayName.trim(),
      "adaptive",
      "gameplay_v2",
    );
    if (!response.ok || !response.data) {
      setError(
        response.error?.message ?? "Failed to create gameplay_v2 session",
      );
      setLoading(false);
      return;
    }

    setSessionId(response.data.session_id);
    setLoading(false);
  };

  if (!sessionId) {
    return (
      <main className="mx-auto flex min-h-screen w-full max-w-xl flex-col items-center justify-center gap-6 px-4">
        <h1 className="text-4xl font-semibold tracking-wide text-neutral-100">
          Silent Frequency
        </h1>
        <p className="text-sm text-neutral-500">
          Batch 4.1 gameplay_v2 vertical slice
        </p>

        <form onSubmit={startGameplayV2} className="w-full space-y-3">
          <input
            value={displayName}
            onChange={(event) => setDisplayName(event.target.value)}
            placeholder="Enter display name"
            className="w-full rounded-md border border-neutral-700 bg-neutral-900 px-4 py-3 text-neutral-100"
          />
          <button
            type="submit"
            disabled={loading || !displayName.trim()}
            className="w-full rounded-md bg-cyan-600 px-4 py-3 font-medium text-white disabled:opacity-50"
          >
            {loading ? "Starting..." : "Start gameplay_v2"}
          </button>
        </form>

        {error && <p className="text-sm text-red-400">{error}</p>}
      </main>
    );
  }

  return (
    <main className="min-h-screen px-4 py-8">
      <PuzzleScreen sessionId={sessionId} />
    </main>
  );
}

/**
 * useAudio — Howler.js audio hook
 *
 * Provides ambient background loop and one-shot SFX playback.
 * Audio files are expected under /public/audio/.
 */

"use client";

import { useRef, useCallback, useEffect } from "react";
import { Howl } from "howler";

interface UseAudioOptions {
  ambientSrc?: string; // path relative to public/
  ambientVolume?: number;
}

export function useAudio({
  ambientSrc = "/audio/ambient.mp3",
  ambientVolume = 0.3,
}: UseAudioOptions = {}) {
  const ambientRef = useRef<Howl | null>(null);
  const sfxRef = useRef<Howl | null>(null);

  // ── Ambient loop ───────────────────────────────────────
  const startAmbient = useCallback(() => {
    if (ambientRef.current) return;
    ambientRef.current = new Howl({
      src: [ambientSrc],
      loop: true,
      volume: ambientVolume,
      html5: true,
    });
    ambientRef.current.play();
  }, [ambientSrc, ambientVolume]);

  const stopAmbient = useCallback(() => {
    ambientRef.current?.stop();
    ambientRef.current?.unload();
    ambientRef.current = null;
  }, []);

  // ── One-shot SFX ──────────────────────────────────────
  const playSfx = useCallback((src: string, volume = 0.6) => {
    sfxRef.current?.unload();
    sfxRef.current = new Howl({ src: [src], volume });
    sfxRef.current.play();
  }, []);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      ambientRef.current?.unload();
      sfxRef.current?.unload();
    };
  }, []);

  return { startAmbient, stopAmbient, playSfx };
}

"use client";

import { useEffect, useRef, useState } from "react";

const STEPS = [1, 2, 5, 10] as const;
const SPEEDS = [
  { label: "¼×", value: 0.25 },
  { label: "½×", value: 0.5 },
  { label: "1×", value: 1 },
] as const;

type Props = {
  frame: number;
  frameCount: number;
  fps: number | null;
  onSeek: (frame: number) => void;
  onStep: (delta: number) => void;
  listenKeys?: boolean;
};

export function Scrubber({
  frame,
  frameCount,
  fps,
  onSeek,
  onStep,
  listenKeys = false,
}: Props) {
  const max = Math.max(0, frameCount - 1);
  const [step, setStep] = useState<(typeof STEPS)[number]>(1);
  const [speed, setSpeed] = useState<(typeof SPEEDS)[number]["value"]>(0.25);
  const [playing, setPlaying] = useState(false);
  const onStepRef = useRef(onStep);
  const onSeekRef = useRef(onSeek);
  onStepRef.current = onStep;
  onSeekRef.current = onSeek;
  const stepRef = useRef(step);
  stepRef.current = step;
  const frameRef = useRef(frame);
  frameRef.current = frame;
  const maxRef = useRef(max);
  maxRef.current = max;

  useEffect(() => {
    if (!playing) return;
    const rate = Math.max(fps && fps > 0 ? fps : 30, 1);
    const ms = Math.max(16, (step / rate / speed) * 1000);
    const id = window.setInterval(() => {
      if (frameRef.current >= maxRef.current) {
        setPlaying(false);
        return;
      }
      onStepRef.current(stepRef.current);
    }, ms);
    return () => window.clearInterval(id);
  }, [playing, step, speed, fps]);

  useEffect(() => {
    if (playing && frame >= max) setPlaying(false);
  }, [playing, frame, max]);

  function togglePlay() {
    if (playing) {
      setPlaying(false);
      return;
    }
    if (frame >= max) onSeek(0);
    setPlaying(true);
  }

  function nudge(dir: number) {
    setPlaying(false);
    onStep(dir * step);
  }

  useEffect(() => {
    if (!listenKeys) return;
    function onKey(e: KeyboardEvent) {
      if (
        e.target instanceof HTMLInputElement ||
        e.target instanceof HTMLTextAreaElement ||
        e.target instanceof HTMLSelectElement
      ) {
        return;
      }
      if (e.key === " " || e.code === "Space") {
        e.preventDefault();
        togglePlay();
      } else if (e.key === "ArrowLeft") {
        e.preventDefault();
        setPlaying(false);
        onStepRef.current(-(e.shiftKey ? 10 : stepRef.current));
      } else if (e.key === "ArrowRight") {
        e.preventDefault();
        setPlaying(false);
        onStepRef.current(e.shiftKey ? 10 : stepRef.current);
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [listenKeys, playing, frame, max]);

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-3">
        <button
          type="button"
          className="flex h-9 w-9 items-center justify-center rounded-md border border-lime/40 bg-lime/10 text-lime"
          onClick={togglePlay}
          aria-label={playing ? "Pause" : "Play"}
        >
          {playing ? (
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden>
              <rect x="6" y="5" width="4" height="14" rx="1" />
              <rect x="14" y="5" width="4" height="14" rx="1" />
            </svg>
          ) : (
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-current" aria-hidden>
              <path d="M8 5.5v13l11-6.5z" />
            </svg>
          )}
        </button>
        <button
          type="button"
          className="rounded-md border border-line px-2 py-1 text-sm text-mute hover:text-chalk"
          onClick={() => nudge(-1)}
          aria-label={`Back ${step} frames`}
        >
          −{step}
        </button>
        <input
          type="range"
          min={0}
          max={max}
          value={Math.min(frame, max)}
          onPointerDown={() => setPlaying(false)}
          onChange={(e) => {
            setPlaying(false);
            onSeek(Number(e.target.value));
          }}
          className="h-2 flex-1 accent-lime"
        />
        <button
          type="button"
          className="rounded-md border border-line px-2 py-1 text-sm text-mute hover:text-chalk"
          onClick={() => nudge(1)}
          aria-label={`Forward ${step} frames`}
        >
          +{step}
        </button>
        <span className="w-28 font-mono text-sm text-chalk">
          {frame}
          <span className="text-mute"> / {max}</span>
        </span>
        {fps != null && (
          <span className="hidden font-mono text-xs text-mute sm:inline">
            {fps.toFixed(2)} fps
          </span>
        )}
      </div>
      <div className="flex flex-wrap items-center gap-4 text-xs">
        <div className="flex items-center gap-1.5">
          <span className="uppercase tracking-[0.14em] text-mute">Step</span>
          {STEPS.map((n) => (
            <button
              key={n}
              type="button"
              onClick={() => setStep(n)}
              className={`rounded-full border px-2.5 py-0.5 ${
                step === n
                  ? "border-lime text-lime"
                  : "border-line text-mute hover:text-chalk"
              }`}
            >
              {n}
            </button>
          ))}
        </div>
        <div className="flex items-center gap-1.5">
          <span className="uppercase tracking-[0.14em] text-mute">Play</span>
          {SPEEDS.map((s) => (
            <button
              key={s.value}
              type="button"
              onClick={() => setSpeed(s.value)}
              className={`rounded-full border px-2.5 py-0.5 ${
                speed === s.value
                  ? "border-lime text-lime"
                  : "border-line text-mute hover:text-chalk"
              }`}
            >
              {s.label}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}

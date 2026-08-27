"use client";

type Props = {
  frame: number;
  frameCount: number;
  fps: number | null;
  onSeek: (frame: number) => void;
  onStep: (delta: number) => void;
};

export function Scrubber({ frame, frameCount, fps, onSeek, onStep }: Props) {
  const max = Math.max(0, frameCount - 1);
  return (
    <div className="flex items-center gap-3">
      <button
        type="button"
        className="rounded-md border border-line px-2 py-1 text-sm text-mute hover:text-chalk"
        onClick={() => onStep(-1)}
        aria-label="Previous frame"
      >
        −1
      </button>
      <input
        type="range"
        min={0}
        max={max}
        value={Math.min(frame, max)}
        onChange={(e) => onSeek(Number(e.target.value))}
        className="h-2 flex-1 accent-lime"
      />
      <button
        type="button"
        className="rounded-md border border-line px-2 py-1 text-sm text-mute hover:text-chalk"
        onClick={() => onStep(1)}
        aria-label="Next frame"
      >
        +1
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
  );
}

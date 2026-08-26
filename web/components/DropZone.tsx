"use client";

import { useCallback, useState } from "react";
import { detectVideoFps } from "@/lib/fps";

type Props = {
  onFile: (file: File) => void;
  busy?: boolean;
};

export function DropZone({ onFile, busy }: Props) {
  const [drag, setDrag] = useState(false);
  const [fpsNote, setFpsNote] = useState<string | null>(null);
  const [blocked, setBlocked] = useState<string | null>(null);

  const handle = useCallback(
    async (file: File) => {
      setBlocked(null);
      setFpsNote(null);
      const fps = await detectVideoFps(file);
      if (fps != null && fps < 60) {
        setBlocked(
          `Detected ${fps.toFixed(0)} fps. SwingFrames needs 60 fps or higher — a downswing is ~0.25s, and 30 fps cannot resolve a velocity peak.`
        );
        return;
      }
      if (fps != null && fps < 120) {
        setFpsNote(
          `${fps.toFixed(0)} fps is accepted, but 120+ fps is recommended. Impact timing may be coarse.`
        );
      } else if (fps != null) {
        setFpsNote(`${fps.toFixed(0)} fps detected.`);
      } else {
        setFpsNote(
          "Could not read framerate in the browser. The server will reject clips below 60 fps."
        );
      }
      onFile(file);
    },
    [onFile]
  );

  return (
    <div>
      <label
        onDragOver={(e) => {
          e.preventDefault();
          setDrag(true);
        }}
        onDragLeave={() => setDrag(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDrag(false);
          const file = e.dataTransfer.files[0];
          if (file) void handle(file);
        }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-16 transition ${
          drag
            ? "border-lime bg-lime/10"
            : "border-line bg-panel hover:border-mute"
        } ${busy ? "pointer-events-none opacity-60" : ""}`}
      >
        <input
          type="file"
          accept="video/*"
          className="hidden"
          disabled={busy}
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) void handle(file);
          }}
        />
        <p className="display text-2xl text-chalk">Drop a swing clip</p>
        <p className="mt-2 max-w-md text-center text-sm text-mute">
          60 fps minimum, 120 fps preferred. Video is analyzed then discarded —
          nothing is stored.
        </p>
      </label>
      {blocked && (
        <p className="mt-3 rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
          {blocked}
        </p>
      )}
      {fpsNote && !blocked && (
        <p className="mt-3 text-sm text-mute">{fpsNote}</p>
      )}
    </div>
  );
}

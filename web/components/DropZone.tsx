"use client";

import { useCallback, useState } from "react";

type Props = {
  onFile: (file: File) => void;
  busy?: boolean;
};

export function DropZone({ onFile, busy }: Props) {
  const [drag, setDrag] = useState(false);

  const handle = useCallback(
    (file: File) => {
      onFile(file);
    },
    [onFile]
  );

  return (
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
        if (file) handle(file);
      }}
      className={`flex cursor-pointer flex-col items-center justify-center rounded-2xl border border-dashed px-6 py-16 transition ${
        drag ? "border-lime bg-lime/10" : "border-line bg-panel hover:border-mute"
      } ${busy ? "pointer-events-none opacity-60" : ""}`}
    >
      <input
        type="file"
        accept="video/*"
        className="hidden"
        disabled={busy}
        onChange={(e) => {
          const file = e.target.files?.[0];
          if (file) handle(file);
        }}
      />
      <p className="display text-2xl text-chalk">Drop a swing clip</p>
      <p className="mt-2 max-w-md text-center text-sm text-mute">
        Phone video is transcoded to H.264 with dense keyframes so you can step
        frame by frame. HEVC .MOV from iPhone is fine.
      </p>
    </label>
  );
}

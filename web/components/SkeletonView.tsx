"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import type { SwingFeatures } from "@/types/api";

const EDGES: Array<[number, number]> = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
  [0, 11],
  [0, 12],
];

export function SkeletonView({ features }: { features: SwingFeatures }) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [frame, setFrame] = useState(0);
  const skel = features.debug_skeleton;
  const n = skel?.landmarks.length ?? 0;

  const bounds = useMemo(() => {
    if (!skel) return null;
    let minX = Infinity,
      maxX = -Infinity,
      minY = Infinity,
      maxY = -Infinity;
    for (const lm of skel.landmarks) {
      for (const pt of lm) {
        const x = pt[0];
        const y = pt[1];
        if (x == null || y == null || !Number.isFinite(x) || !Number.isFinite(y))
          continue;
        minX = Math.min(minX, x);
        maxX = Math.max(maxX, x);
        minY = Math.min(minY, y);
        maxY = Math.max(maxY, y);
      }
    }
    if (!Number.isFinite(minX)) return null;
    return { minX, maxX, minY, maxY };
  }, [skel]);

  useEffect(() => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || !skel || !bounds) return;
    const { width, height } = canvas;
    ctx.fillStyle = "#141c18";
    ctx.fillRect(0, 0, width, height);
    const pad = 28;
    const spanX = Math.max(bounds.maxX - bounds.minX, 0.2);
    const spanY = Math.max(bounds.maxY - bounds.minY, 0.2);
    const scale = Math.min(
      (width - pad * 2) / spanX,
      (height - pad * 2) / spanY
    );
    const cx = (bounds.minX + bounds.maxX) / 2;
    const cy = (bounds.minY + bounds.maxY) / 2;
    const to = (x: number, y: number): [number, number] => [
      width / 2 + (x - cx) * scale,
      height / 2 + (y - cy) * scale,
    ];
    const lm = skel.landmarks[Math.min(frame, n - 1)];
    ctx.strokeStyle = "#c6f54e";
    ctx.lineWidth = 2;
    for (const [a, b] of EDGES) {
      const pa = lm[a];
      const pb = lm[b];
      if (!pa || !pb) continue;
      if (![pa[0], pa[1], pb[0], pb[1]].every(Number.isFinite)) continue;
      const [x1, y1] = to(pa[0], pa[1]);
      const [x2, y2] = to(pb[0], pb[1]);
      ctx.beginPath();
      ctx.moveTo(x1, y1);
      ctx.lineTo(x2, y2);
      ctx.stroke();
    }
    ctx.fillStyle = "#e7efe8";
    for (const pt of lm) {
      if (!pt || !Number.isFinite(pt[0]) || !Number.isFinite(pt[1])) continue;
      const [x, y] = to(pt[0], pt[1]);
      ctx.beginPath();
      ctx.arc(x, y, 3, 0, Math.PI * 2);
      ctx.fill();
    }
  }, [bounds, frame, n, skel]);

  if (!skel || n === 0) {
    return (
      <p className="text-sm text-mute">No skeleton debug data for this swing.</p>
    );
  }

  return (
    <div>
      <canvas
        ref={canvasRef}
        width={520}
        height={360}
        className="w-full rounded-xl border border-line bg-panel"
      />
      <input
        type="range"
        min={0}
        max={n - 1}
        value={frame}
        onChange={(e) => setFrame(Number(e.target.value))}
        className="mt-3 w-full accent-lime"
      />
      <p className="mt-1 text-xs text-mute">
        Frame {frame + 1} / {n}
        {skel.timestamps[frame] != null
          ? ` · ${skel.timestamps[frame].toFixed(2)} s`
          : ""}
        . World landmarks, scaled. For inspection, not scoring.
      </p>
    </div>
  );
}

"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import type { SwingOut, SyncMode } from "@/types/api";
import { AnnotationCanvas } from "@/components/canvas/AnnotationCanvas";
import { Scrubber } from "@/components/player/Scrubber";
import { VideoPlayer, clampFrame } from "@/components/player/VideoPlayer";

function mapFrame(
  frameA: number,
  swingA: SwingOut,
  swingB: SwingOut,
  mode: SyncMode,
  anchorA: number,
  anchorB: number
): number {
  const fpsA = swingA.fps ?? 30;
  const fpsB = swingB.fps ?? 30;
  const countA = swingA.frame_count ?? 1;
  const countB = swingB.frame_count ?? 1;
  if (mode === "offset") {
    return clampFrame(
      Math.round((frameA - anchorA) * (fpsB / fpsA)) + anchorB,
      countB
    );
  }
  if (mode === "normalized") {
    const p = frameA / Math.max(countA - 1, 1);
    return clampFrame(Math.round(p * (countB - 1)), countB);
  }
  return 0;
}

function Pane({
  swing,
  frame,
  seekFrame,
  seekToken,
  onPresented,
  annotations,
}: {
  swing: SwingOut;
  frame: number;
  seekFrame: number;
  seekToken: number;
  onPresented?: (n: number) => void;
  annotations: Awaited<ReturnType<typeof api.listAnnotations>>;
}) {
  const w = swing.width ?? 16;
  const h = swing.height ?? 9;
  const fps = swing.fps ?? 30;
  const count = swing.frame_count ?? 1;
  return (
    <div className="flex justify-center">
      <div
        className="relative overflow-hidden rounded-2xl border border-line bg-black"
        style={{
          width: `min(100%, calc(20rem * ${w} / ${h}))`,
          aspectRatio: `${w} / ${h}`,
        }}
      >
        <VideoPlayer
          src={api.mediaUrl(swing.id)}
          fps={fps}
          frameCount={count}
          seekFrame={seekFrame}
          seekToken={seekToken}
          onPresentedFrame={onPresented}
          className="absolute inset-0 h-full w-full object-contain"
        />
        <AnnotationCanvas
          annotations={annotations}
          frame={frame}
          intrinsicW={w}
          intrinsicH={h}
          tool="none"
          draft={[]}
          onDraft={() => undefined}
          onComplete={() => undefined}
        />
      </div>
    </div>
  );
}

export function CompareView({
  swingA,
  swingB,
}: {
  swingA: SwingOut;
  swingB: SwingOut;
}) {
  const [mode, setMode] = useState<SyncMode>("independent");
  const [frameA, setFrameA] = useState(0);
  const [frameB, setFrameB] = useState(0);
  const [seekA, setSeekA] = useState({ frame: 0, token: 0 });
  const [seekB, setSeekB] = useState({ frame: 0, token: 0 });
  const [anchorA, setAnchorA] = useState(0);
  const [anchorB, setAnchorB] = useState(0);
  const [annsA, setAnnsA] = useState<Awaited<ReturnType<typeof api.listAnnotations>>>([]);
  const [annsB, setAnnsB] = useState<Awaited<ReturnType<typeof api.listAnnotations>>>([]);

  useEffect(() => {
    void api.listAnnotations(swingA.id).then(setAnnsA);
    void api.listAnnotations(swingB.id).then(setAnnsB);
  }, [swingA.id, swingB.id]);

  const goA = useCallback(
    (n: number) => {
      const f = clampFrame(n, swingA.frame_count ?? 1);
      setFrameA(f);
      setSeekA((s) => ({ frame: f, token: s.token + 1 }));
      if (mode !== "independent") {
        const mapped = mapFrame(f, swingA, swingB, mode, anchorA, anchorB);
        setFrameB(mapped);
        setSeekB((s) => ({ frame: mapped, token: s.token + 1 }));
      }
    },
    [mode, swingA, swingB, anchorA, anchorB]
  );

  const goB = useCallback(
    (n: number) => {
      const f = clampFrame(n, swingB.frame_count ?? 1);
      setFrameB(f);
      setSeekB((s) => ({ frame: f, token: s.token + 1 }));
    },
    [swingB]
  );

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-3 text-sm">
        {(["independent", "offset", "normalized"] as SyncMode[]).map((m) => (
          <button
            key={m}
            type="button"
            onClick={() => setMode(m)}
            className={`rounded-full border px-3 py-1 ${
              mode === m ? "border-lime text-lime" : "border-line text-mute"
            }`}
          >
            {m}
          </button>
        ))}
        {mode === "offset" && (
          <>
            <button
              type="button"
              className="rounded border border-line px-2 py-1 text-mute"
              onClick={() => setAnchorA(frameA)}
            >
              Anchor A = {anchorA}
            </button>
            <button
              type="button"
              className="rounded border border-line px-2 py-1 text-mute"
              onClick={() => setAnchorB(frameB)}
            >
              Anchor B = {anchorB}
            </button>
          </>
        )}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.16em] text-mute">
            {swingA.filename ?? "Swing A"}
          </p>
          <Pane
            swing={swingA}
            frame={frameA}
            seekFrame={seekA.frame}
            seekToken={seekA.token}
            onPresented={mode === "independent" ? setFrameA : setFrameA}
            annotations={annsA}
          />
          <div className="mt-2">
            <Scrubber
              frame={frameA}
              frameCount={swingA.frame_count ?? 1}
              fps={swingA.fps}
              onSeek={goA}
              onStep={(d) => goA(frameA + d)}
              listenKeys
            />
          </div>
        </div>
        <div>
          <p className="mb-2 text-xs uppercase tracking-[0.16em] text-mute">
            {swingB.filename ?? "Swing B"}
          </p>
          <Pane
            swing={swingB}
            frame={frameB}
            seekFrame={seekB.frame}
            seekToken={seekB.token}
            onPresented={mode === "independent" ? setFrameB : undefined}
            annotations={annsB}
          />
          <div className="mt-2">
            {mode === "independent" ? (
              <Scrubber
                frame={frameB}
                frameCount={swingB.frame_count ?? 1}
                fps={swingB.fps}
                onSeek={goB}
                onStep={(d) => goB(frameB + d)}
              />
            ) : (
              <p className="font-mono text-sm text-mute">
                {frameB} / {(swingB.frame_count ?? 1) - 1} · driven by A
              </p>
            )}
          </div>
        </div>
      </div>
      {mode !== "independent" && (
        <p className="text-xs text-mute">
          One controller owns the frame index. Swing B is derived and never
          drives A.
        </p>
      )}
    </div>
  );
}

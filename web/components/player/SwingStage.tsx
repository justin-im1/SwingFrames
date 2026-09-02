"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { OUTCOMES } from "@/lib/format";
import type {
  AnnotationKind,
  AnnotationOut,
  OutcomeResult,
  Point,
  SwingOut,
} from "@/types/api";
import { AnnotationCanvas } from "@/components/canvas/AnnotationCanvas";
import { Scrubber } from "@/components/player/Scrubber";
import { VideoPlayer, clampFrame } from "@/components/player/VideoPlayer";

type Tool = AnnotationKind | "none";

const TOOLS: { id: Tool; label: string }[] = [
  { id: "line", label: "Line" },
  { id: "angle", label: "Angle" },
  { id: "circle", label: "Circle" },
  { id: "freehand", label: "Path" },
];

export function SwingStage({ swing }: { swing: SwingOut }) {
  const fps = swing.fps ?? 30;
  const frameCount = swing.frame_count ?? 1;
  const [frame, setFrame] = useState(0);
  const [seek, setSeek] = useState({ frame: 0, token: 0 });
  const [tool, setTool] = useState<Tool>("none");
  const [draft, setDraft] = useState<Point[]>([]);
  const [items, setItems] = useState<AnnotationOut[]>([]);
  const [undo, setUndo] = useState<AnnotationOut[]>([]);
  const [redo, setRedo] = useState<AnnotationOut[]>([]);
  const [stickyNext, setStickyNext] = useState(true);
  const [outcome, setOutcome] = useState<OutcomeResult | null>(null);
  const [error, setError] = useState<string | null>(null);

  const go = useCallback(
    (next: number) => {
      const f = clampFrame(next, frameCount);
      setFrame(f);
      setSeek((s) => ({ frame: f, token: s.token + 1 }));
    },
    [frameCount]
  );

  useEffect(() => {
    void (async () => {
      try {
        const [anns, oc] = await Promise.all([
          api.listAnnotations(swing.id),
          api.getOutcome(swing.id),
        ]);
        setItems(anns);
        setOutcome(oc?.result ?? null);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Could not load drawings.");
      }
    })();
  }, [swing.id]);

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) {
        return;
      }
      if (e.key === "ArrowLeft" || e.key === "ArrowRight" || e.key === " ") {
        return;
      }
      if ((e.metaKey || e.ctrlKey) && e.key === "z") {
        e.preventDefault();
        if (e.shiftKey) void redoLast();
        else void undoLast();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [frame, go, items, undo, redo]);

  async function persist(kind: AnnotationKind, points: Point[]) {
    const created = await api.createAnnotation(swing.id, {
      frame,
      kind,
      points,
      sticky: stickyNext,
    });
    setItems((prev) => [...prev, created]);
    setUndo((prev) => [...prev, created]);
    setRedo([]);
  }

  async function undoLast() {
    const last = undo[undo.length - 1];
    if (!last) return;
    await api.deleteAnnotation(last.id);
    setItems((prev) => prev.filter((a) => a.id !== last.id));
    setUndo((prev) => prev.slice(0, -1));
    setRedo((prev) => [...prev, last]);
  }

  async function redoLast() {
    const last = redo[redo.length - 1];
    if (!last) return;
    const created = await api.createAnnotation(swing.id, {
      frame: last.frame,
      kind: last.kind,
      points: last.points,
      sticky: last.sticky,
      label: last.label,
      style: last.style,
    });
    setItems((prev) => [...prev, created]);
    setUndo((prev) => [...prev, created]);
    setRedo((prev) => prev.slice(0, -1));
  }

  async function clearAll() {
    if (items.length === 0) return;
    await api.clearAnnotations(swing.id);
    setItems([]);
    setUndo([]);
    setRedo([]);
    setDraft([]);
  }

  const w = swing.width ?? 16;
  const h = swing.height ?? 9;

  return (
    <div className="space-y-4">
      <div className="flex justify-center">
        <div
          className="relative overflow-hidden rounded-2xl border border-line bg-black"
          style={{
            width: `min(40rem, 100%, calc(26rem * ${w} / ${h}))`,
            aspectRatio: `${w} / ${h}`,
          }}
        >
          <VideoPlayer
            src={api.mediaUrl(swing.id)}
            fps={fps}
            frameCount={frameCount}
            seekFrame={seek.frame}
            seekToken={seek.token}
            onPresentedFrame={setFrame}
            className="absolute inset-0 h-full w-full object-contain"
          />
          <AnnotationCanvas
            annotations={items}
            frame={frame}
            intrinsicW={w}
            intrinsicH={h}
            tool={tool}
            draft={draft}
            onDraft={setDraft}
            onComplete={(points) => void persist(tool as AnnotationKind, points)}
          />
        </div>
      </div>
      <Scrubber
        frame={frame}
        frameCount={frameCount}
        fps={swing.fps}
        onSeek={go}
        onStep={(d) => go(frame + d)}
        listenKeys
      />
      <div className="flex flex-wrap gap-2">
        {TOOLS.map((t) => (
          <button
            key={t.id}
            type="button"
            onClick={() => {
              setTool((current) => (current === t.id ? "none" : t.id));
              setDraft([]);
            }}
            className={`rounded-full border px-3 py-1 text-sm ${
              tool === t.id
                ? "border-lime bg-lime/15 text-lime"
                : "border-line text-mute hover:text-chalk"
            }`}
          >
            {t.label}
          </button>
        ))}
        <label className="ml-auto flex items-center gap-2 text-sm text-mute">
          <input
            type="checkbox"
            checked={!stickyNext}
            onChange={(e) => setStickyNext(!e.target.checked)}
          />
          This frame only
        </label>
        <button type="button" className="text-sm text-mute hover:text-chalk" onClick={() => void undoLast()}>
          Undo
        </button>
        <button type="button" className="text-sm text-mute hover:text-chalk" onClick={() => void redoLast()}>
          Redo
        </button>
        <button
          type="button"
          className="text-sm text-mute hover:text-chalk disabled:opacity-40"
          disabled={items.length === 0}
          onClick={() => void clearAll()}
        >
          Clear all
        </button>
      </div>

      <section className="rounded-2xl border border-line bg-panel p-4">
        <h3 className="text-sm uppercase tracking-[0.16em] text-mute">Ball flight</h3>
        <p className="mt-1 text-sm text-mute">
          What you saw. Tagged as an observation, not a diagnosis.
        </p>
        <div className="mt-3 flex flex-wrap gap-2">
          {OUTCOMES.map((o) => (
            <button
              key={o}
              type="button"
              onClick={() => {
                setOutcome(o);
                void api.tagOutcome(swing.id, o);
              }}
              className={`rounded-full border px-3 py-1 text-sm ${
                outcome === o
                  ? "border-lime bg-lime/15 text-lime"
                  : "border-line text-mute hover:text-chalk"
              }`}
            >
              {o}
            </button>
          ))}
        </div>
      </section>
      {error && (
        <p className="rounded-lg border border-bad/40 bg-bad/10 px-3 py-2 text-sm text-bad">
          {error}
        </p>
      )}
    </div>
  );
}
